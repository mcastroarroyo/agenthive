"""Publish the knowledge-base corpus to Vertex AI Search (one data store per realm).

    HIVE_PROJECT=<project> .venv/bin/python deploy/sync_kb.py [realm ...]

Markdown in agenthive/grounding/corpus/<realm>/ -> HTML in gs://<project>-agenthive/kb/<realm>/ -> documents:import
(FULL reconciliation, so deleted docs disappear). Uses gcloud for auth (no local ADC needed).
"""
from __future__ import annotations

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
CORPUS = ROOT / "agenthive" / "grounding" / "corpus"
P = os.environ["HIVE_PROJECT"]
PREFIX = os.environ.get("HIVE_KB_PREFIX", "agenthive-kb")
BUCKET = f"gs://{P}-agenthive"


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


def sync(realm: str) -> None:
    src = CORPUS / realm
    docs = sorted(src.glob("*.md"))
    if not docs:
        print(f"[{realm}] no corpus docs, skipped")
        return
    with tempfile.TemporaryDirectory() as tmp:
        for d in docs:
            (Path(tmp) / f"{d.stem}.html").write_text(md_to_html(d.read_text()))
        dest = f"{BUCKET}/kb/{realm}/"
        subprocess.run(["gcloud", "storage", "rm", "--quiet", f"{dest}**"], capture_output=True)
        subprocess.run(["gcloud", "storage", "cp", "--quiet", *[str(p) for p in Path(tmp).glob("*.html")], dest],
                       check=True, capture_output=True)
    base = (f"https://discoveryengine.googleapis.com/v1/projects/{P}/locations/global/collections/default_collection/"
            f"dataStores/{PREFIX}-{realm}/branches/default_branch/documents:import")
    op = api("POST", base, {"gcsSource": {"inputUris": [f"{BUCKET}/kb/{realm}/*.html"], "dataSchema": "content"},
                            "reconciliationMode": "FULL"})
    name = op["name"]
    for _ in range(60):
        st = api("GET", f"https://discoveryengine.googleapis.com/v1/{name}")
        if st.get("done"):
            meta = st.get("metadata", {})
            print(f"[{realm}] {len(docs)} docs -> success={meta.get('successCount', 0)} "
                  f"failure={meta.get('failureCount', 0)} {st.get('error', '')}")
            return
        time.sleep(10)
    print(f"[{realm}] import still running: {name}")


if __name__ == "__main__":
    realms = sys.argv[1:] or [p.name for p in sorted(CORPUS.iterdir()) if p.is_dir()]
    for r in realms:
        sync(r)
