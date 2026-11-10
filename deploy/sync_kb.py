"""Publish the knowledge-base corpus to Vertex AI Search — one data store per internal realm, shared by editions.

    HIVE_PROJECT=<project> .venv/bin/python deploy/sync_kb.py [store ...]      # store = internal realm id

Each store holds the realm's own docs (edition "internal") plus the docs of every showcase segment hosted on it
(edition "showcase"; see kb_store / kb_sources in catalog/editions/showcase/hive.yaml). A doc used by both editions is
stored once. Markdown -> HTML in gs://<project>-agenthive/kb/<store>/ + documents.jsonl with
structData.editions -> documents:import (FULL reconciliation, so removed docs disappear). Agents filter with
editions: ANY("<edition>"). Uses gcloud for auth (no local ADC needed).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agenthive.catalog import load_catalog  # noqa: E402
from agenthive.grounding import HERE as GROUNDING, corpus_files  # noqa: E402
from agenthive.settings import EDITIONS, get_settings  # noqa: E402

P = os.environ["HIVE_PROJECT"]
PREFIX = get_settings().kb_prefix
BUCKET = f"gs://{P}-agenthive"
API = "https://discoveryengine.googleapis.com/v1"
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "title": {"type": "string", "keyPropertyMapping": "title", "retrievable": True},
        "editions": {"type": "array", "items": {"type": "string", "indexable": True, "retrievable": True}},
    },
}


def md_to_html(md: str) -> str:
    lines, out, in_list, in_table = md.splitlines(), [], False, False
    title = next((l.lstrip("# ").strip() for l in lines if l.startswith("#")), "Document")

    def inline(t: str) -> str:
        t = html.escape(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        return t

    for l in lines:
        s = l.rstrip()
        if in_list and not re.match(r"^\s*([-*]|\d+\.)\s", s):
            out.append("</ul>")
            in_list = False
        if in_table and not s.startswith("|"):
            out.append("</table>")
            in_table = False
        if m := re.match(r"^(#{1,6})\s+(.*)", s):
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif re.match(r"^\s*([-*]|\d+\.)\s", s):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(re.sub(r'^\s*([-*]|\d+\.)\s', '', s))}</li>")
        elif s.startswith("|"):
            if re.match(r"^\|[\s:\-|]+\|$", s):
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
            cells = [c.strip() for c in s.strip("|").split("|")]
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
        elif s:
            out.append(f"<p>{inline(s)}</p>")
    if in_list:
        out.append("</ul>")
    if in_table:
        out.append("</table>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title></head>"
            f"<body>{''.join(out)}</body></html>")


def token() -> str:
    return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()


def api(method: str, url: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token()}", "X-Goog-User-Project": P,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"{}")


def store_docs(store: str) -> list[dict]:
    """Documents for one data store: id, source path and the editions that use it."""
    eds: dict[Path, set[str]] = {}
    for edition in EDITIONS:
        cat = load_catalog(edition)
        for seg in cat.realms:
            if (seg.kb_store or seg.id) != store:
                continue
            for path in corpus_files(seg.id, edition).values():
                eds.setdefault(path, set()).add(edition)
    out = []
    for path, editions in sorted(eds.items()):
        rel = str(path.relative_to(GROUNDING).with_suffix(""))
        doc_id = f"{re.sub(r'[^a-zA-Z0-9_-]', '-', path.stem)[:44]}-{hashlib.sha1(rel.encode()).hexdigest()[:10]}"
        out.append({"id": doc_id, "path": path, "editions": sorted(editions)})
    return out


def wait(op: dict, what: str) -> dict:
    name = op.get("name")
    for _ in range(90):
        if op.get("done") or not name:
            return op
        time.sleep(10)
        op = api("GET", f"{API}/{name}")
    raise SystemExit(f"{what}: still running ({name})")


def sync(store: str) -> None:
    docs = store_docs(store)
    if not docs:
        print(f"[{store}] no corpus docs, skipped")
        return
    base = f"{API}/projects/{P}/locations/global/collections/default_collection/dataStores/{PREFIX}-{store}"
    wait(api("PATCH", f"{base}/schemas/default_schema", {"structSchema": SCHEMA}), f"[{store}] schema")
    dest = f"{BUCKET}/kb/{store}/"
    with tempfile.TemporaryDirectory() as tmp:
        lines = []
        for d in docs:
            text = d["path"].read_text()
            title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("#")), d["path"].stem)
            (Path(tmp) / f"{d['id']}.html").write_text(md_to_html(text))
            lines.append(json.dumps({"id": d["id"], "structData": {"title": title, "editions": d["editions"]},
                                     "content": {"mimeType": "text/html", "uri": f"{dest}{d['id']}.html"}}))
        (Path(tmp) / "documents.jsonl").write_text("\n".join(lines) + "\n")
        subprocess.run(["gcloud", "storage", "rm", "--quiet", f"{dest}**"], capture_output=True)
        subprocess.run(["gcloud", "storage", "cp", "--quiet", *[str(x) for x in Path(tmp).iterdir()], dest],
                       check=True, capture_output=True)
    op = api("POST", f"{base}/branches/default_branch/documents:import",
             {"gcsSource": {"inputUris": [f"{dest}documents.jsonl"], "dataSchema": "document"},
              "reconciliationMode": "FULL"})
    st = wait(op, f"[{store}] import")
    meta = st.get("metadata", {})
    split = {e: sum(e in d["editions"] for d in docs) for e in EDITIONS}
    print(f"[{store}] {len(docs)} docs ({', '.join(f'{k} {v}' for k, v in split.items())}) -> "
          f"success={meta.get('successCount', 0)} failure={meta.get('failureCount', 0)} {st.get('error', '')}")


if __name__ == "__main__":
    stores = sys.argv[1:] or [r.id for r in load_catalog("internal").realms]
    for st in stores:
        sync(st)
