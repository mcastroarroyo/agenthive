"""Load the synthetic demo warehouse into BigQuery.

    HIVE_PROJECT=<project> .venv/bin/python deploy/seed_bigquery.py [table ...]

Schemas: agenthive/grounding/bq/*.json. Rows: deploy/seed/bq_*.py -> tables() (deterministic). Tables are replaced.
Uses the bq CLI (gcloud auth), so no local ADC is needed.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = os.environ["HIVE_PROJECT"]
DATASET = os.environ.get("HIVE_BQ_DATASET", "agenthive_demo")
LOCATION = os.environ.get("HIVE_REGION", "us-central1")


def schemas() -> dict:
    out = {}
    for p in sorted((ROOT / "agenthive" / "grounding" / "bq").glob("*.json")):
        out.update(json.loads(p.read_text()))
    return out


def rows() -> dict:
    out = {}
    for p in sorted((ROOT / "deploy" / "seed").glob("bq_*.py")):
        spec = importlib.util.spec_from_file_location(p.stem, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out.update(mod.tables())
    return out


def main(only: list[str]) -> None:
    sch, data = schemas(), rows()
    missing = sorted(set(sch) - set(data))
    if missing:
        print("WARNING: schemas without seed rows:", missing)
    for table, meta in sch.items():
        if only and table not in only or table not in data:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            nd = Path(tmp) / f"{table}.json"
            nd.write_text("\n".join(json.dumps(r, default=str) for r in data[table]))
            schema_file = Path(tmp) / "schema.json"
            schema_file.write_text(json.dumps([{"name": c["name"], "type": c["type"],
                                                "description": c.get("description", "")[:1000]}
                                               for c in meta["columns"]]))
            subprocess.run(["bq", f"--project_id={P}", f"--location={LOCATION}", "load", "--replace",
                            "--source_format=NEWLINE_DELIMITED_JSON", f"{P}:{DATASET}.{table}", str(nd),
                            str(schema_file)], check=True, capture_output=True, text=True)
            subprocess.run(["bq", f"--project_id={P}", "update", "--description", meta["description"][:1000],
                            "--set_label", "app:agenthive", f"{P}:{DATASET}.{table}"], check=True,
                           capture_output=True, text=True)
        print(f"loaded {table}: {len(data[table])} rows")


if __name__ == "__main__":
    main(sys.argv[1:])
