"""The "Grounding" building block: knowledge sources an agent can retrieve from.

  kb             Vertex AI Search data store for the agent's realm (synthetic playbooks, policies, product docs)
  google_search  Grounding with Google Search for current public facts (returns citations)
  bigquery[:t1,t2]  read-only BigQuery over the synthetic demo warehouse (named tables only)
  fixtures       synthetic system-of-record data reached through the agent's own function tools
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import google.auth
import google.auth.credentials

from ..settings import get_settings

HERE = Path(__file__).resolve().parent
# BigQuery table registry: grounding/bq/<realm>.json -> {table: {"description": str, "columns": [{name, type, description}]}}
BQ_TABLES: dict[str, dict] = {}
for _p in sorted((HERE / "bq").glob("*.json")):
    BQ_TABLES.update(json.loads(_p.read_text()))


class RuntimeADC(google.auth.credentials.Credentials):
    """Application Default Credentials resolved where the agent runs — never pickled from the deploying machine."""

    def __init__(self):
        super().__init__()
        self._inner = None

    def _creds(self):
        if self._inner is None:
            self._inner, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        return self._inner

    def refresh(self, request):
        c = self._creds()
        if not c.valid:
            c.refresh(request)
        self.token, self.expiry = c.token, c.expiry

    def __getstate__(self):
        return {}

    def __setstate__(self, state):
        google.auth.credentials.Credentials.__init__(self)
        self._inner = None


def corpus_files(realm: str, edition: str | None = None) -> dict[str, Path]:
    """Markdown docs that make up a realm's (or segment's) knowledge base, by file name.

    internal: grounding/corpus/<realm>/*.md. Editions: the segment's kb_sources folders, minus kb_exclude, plus
    grounding/editions/<edition>/corpus/<segment>/*.md (same name replaces)."""
    from ..catalog import load_catalog
    from ..settings import get_settings

    ed = edition or get_settings().edition
    corpus = HERE / "corpus"
    if ed == "internal":
        return {p.name: p for p in sorted((corpus / realm).glob("*.md"))}
    seg = load_catalog(ed).realm(realm)
    out: dict[str, Path] = {}
    for src in seg.kb_sources:
        out.update({p.name: p for p in sorted((corpus / src).glob("*.md")) if p.name not in seg.kb_exclude})
    out.update({p.name: p for p in sorted((HERE / "editions" / ed / "corpus" / realm).glob("*.md"))})
    return dict(sorted(out.items()))


def kb_store(realm: str) -> str:
    """The data store hosting a realm's KB: the realm itself (internal) or the segment's kb_store (editions)."""
    from ..catalog import load_catalog

    s = get_settings()
    return realm if s.edition == "internal" else (load_catalog().realm(realm).kb_store or realm)


def kb_filter() -> str:
    """Each document lists the editions it belongs to (structData.editions); agents only see their edition's."""
    return f'editions: ANY("{get_settings().edition}")'


def kb_tool(realm: str):
    from google.adk.tools.vertex_ai_search_tool import VertexAiSearchTool

    return VertexAiSearchTool(data_store_id=get_settings().kb_data_store(kb_store(realm)), filter=kb_filter(),
                              max_results=5, bypass_multi_tools_limit=True)


def google_search_tool():
    from google.adk.tools.google_search_tool import GoogleSearchTool

    return GoogleSearchTool(bypass_multi_tools_limit=True)


def bigquery_toolset(agent_id: str):
    from google.adk.integrations.bigquery import BigQueryCredentialsConfig, BigQueryToolset
    from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode

    s = get_settings()
    return BigQueryToolset(
        credentials_config=BigQueryCredentialsConfig(credentials=RuntimeADC()),
        bigquery_tool_config=BigQueryToolConfig(
            write_mode=WriteMode.BLOCKED, location=s.region, compute_project_id=s.project or None,
            default_project_id=s.project or None, maximum_bytes_billed=500_000_000, max_query_result_rows=100,
            application_name="agenthive",
            job_labels={"app": "agenthive", "agent": re.sub(r"[^a-z0-9_-]", "_", agent_id.lower())[:63]}),
        tool_filter=["execute_sql", "get_table_info"],
    )


def bigquery_brief(tables: list[str]) -> str:
    """Schema notes injected into the instruction so the model writes correct SQL on the first try."""
    s = get_settings()
    qualified = s.edition == "internal"        # the showcase never shows the hosting project's id to clients
    ds = f"{s.project}.{s.bq_dataset}" if qualified else s.bq_dataset
    lines = [f"BigQuery dataset `{ds}` (read-only, synthetic data). Tables:"]
    for t in tables:
        meta = BQ_TABLES.get(t)
        if not meta:
            continue
        cols = ", ".join(f"{c['name']} {c['type']}" for c in meta["columns"])
        lines.append(f"- `{s.bq_dataset}.{t}` — {meta['description']} Columns: {cols}")
    lines.append(("Always use fully-qualified table names with the project shown above." if qualified else
                  f"Always write table names as `{s.bq_dataset}.<table>` (the project is set for you; never add one).")
                 + " Aggregate in SQL; at most 3 queries per question; never invent numbers that no query returned.")
    return "\n".join(lines)


def describe(spec: str, realm: str) -> dict:
    """Human-readable description of one grounding entry (for the UI's Grounding card)."""
    kind, _, arg = spec.partition(":")
    s = get_settings()
    if kind == "kb":
        return {"kind": kind, "label": "Vertex AI Search", "detail": f"Data store {s.kb_prefix}-{kb_store(realm)} — "
                f"{realm} playbooks, policies and product docs (synthetic)"}
    if kind == "google_search":
        return {"kind": kind, "label": "Google Search", "detail": "Grounding with Google Search, cited sources"}
    if kind == "bigquery":
        tables = [t for t in arg.split(",") if t]
        return {"kind": kind, "label": "BigQuery", "detail": f"{s.bq_dataset}: " + (", ".join(tables) or "all tables")}
    return {"kind": kind, "label": "Systems of record (synthetic)", "detail": arg or "demo data behind function tools"}
