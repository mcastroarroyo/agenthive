"""Deploy (or update in place) one Agent Engine per realm — the "Runtime" building block.

    HIVE_PROJECT=<project> GCLOUD_ACCESS_TOKEN=$(gcloud auth print-access-token) \
        .venv/bin/python deploy/deploy_engines.py [realm ...] [--min-instances 0]
    ... deploy/deploy_engines.py --list
    ... deploy/deploy_engines.py --ask platform workspace_pro "Triage my inbox"

Each engine hosts a HiveRouter with every agent of the realm (AdkApp, managed sessions). Engines are found by display
name ("Agent Hive · <Realm>"), so re-running updates the same resource and keeps its URL/ID stable.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

P = os.environ["HIVE_PROJECT"]
REGION = os.environ.get("HIVE_REGION", "us-central1")                 # BigQuery / Cloud Run region
ENGINE_REGION = os.environ.get("HIVE_ENGINE_REGION", "us-east4")      # Agent Engine region (own quota pool)
STAGING = f"gs://{P}-agenthive-{ENGINE_REGION}"
RUNTIME_SA = f"agenthive-runtime@{P}.iam.gserviceaccount.com"
REQUIREMENTS = [
    "google-adk==2.12.0",
    "google-cloud-aiplatform[adk,agent_engines]==2.5.0",
    "google-cloud-discoveryengine==0.20.6",
    "cloudpickle==3.1.2",
    "pyyaml>=6.0",
]


def credentials():
    token = os.environ.get("GCLOUD_ACCESS_TOKEN")
    if not token:
        return None
    import google.auth
    from google.oauth2.credentials import Credentials

    cred = Credentials(token=token)
    google.auth.default = lambda *a, **k: (cred, P)   # SDK paths that call ADC directly (staging upload)
    return cred


def display_name(realm_name: str) -> str:
    return f"Agent Hive · {realm_name}"


def engines() -> dict[str, str]:
    from vertexai import agent_engines

    return {e.display_name: e.resource_name for e in agent_engines.list() if e.display_name.startswith("Agent Hive · ")}


def deploy(realm_id: str, min_instances: int) -> str:
    from vertexai import agent_engines

    from agenthive.catalog import load_catalog
    from agenthive.router import build_realm_root

    realm = load_catalog().realm(realm_id)
    root = build_realm_root(realm_id)
    app = agent_engines.AdkApp(agent=root)
    os.chdir(ROOT)  # extra_packages are relative paths
    kwargs = dict(
        agent_engine=app,
        requirements=REQUIREMENTS,
        extra_packages=["agenthive"],
        gcs_dir_name=f"agent_engine/{realm_id}",   # per-realm staging so realms can deploy in parallel
        display_name=display_name(realm.name),
        description=f"Wursta Agent Hive — {realm.name}: {len(realm.agents)} agents. {realm.blurb}"[:1000],
        service_account=RUNTIME_SA,
        min_instances=min_instances,
        max_instances=3,
        env_vars={
            "HIVE_PROJECT": P,
            "HIVE_REGION": REGION,
            "HIVE_ENGINE_REGION": ENGINE_REGION,
            "HIVE_MODEL_LOCATION": os.environ.get("HIVE_MODEL_LOCATION", "global"),
            "HIVE_BQ_DATASET": os.environ.get("HIVE_BQ_DATASET", "agenthive_demo"),
            "HIVE_KB_PREFIX": os.environ.get("HIVE_KB_PREFIX", "agenthive-kb"),
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        },
    )
    existing = engines().get(display_name(realm.name))
    eng = agent_engines.update(resource_name=existing, **kwargs) if existing else agent_engines.create(**kwargs)
    print(f"{realm_id}: {eng.resource_name}", flush=True)
    return eng.resource_name


def ask(realm_id: str, agent_id: str, message: str) -> None:
    from vertexai import agent_engines

    from agenthive.catalog import load_catalog

    realm = load_catalog().realm(realm_id)
    eng = agent_engines.get(engines()[display_name(realm.name)])
    s = eng.create_session(user_id="cli", state={"hive_agent": load_catalog().agent(agent_id).adk_name})
    for ev in eng.stream_query(user_id="cli", session_id=s["id"], message=message):
        for part in (ev.get("content") or {}).get("parts", []):
            if "function_call" in part:
                print("→", ev.get("author"), part["function_call"]["name"],
                      json.dumps(part["function_call"].get("args"), ensure_ascii=False)[:200])
            elif part.get("text") and not part.get("thought"):
                print(f"[{ev.get('author')}]", part["text"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("realms", nargs="*")
    ap.add_argument("--min-instances", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--ask", nargs=3, metavar=("REALM", "AGENT", "MESSAGE"))
    a = ap.parse_args()

    import vertexai

    vertexai.init(project=P, location=ENGINE_REGION, staging_bucket=STAGING, credentials=credentials())
    if a.list:
        print(json.dumps(engines(), indent=2))
        return
    if a.ask:
        ask(*a.ask)
        return
    from agenthive.catalog import load_catalog

    realms = a.realms or [r.id for r in load_catalog().realms if r.agents]
    out = {r: deploy(r, a.min_instances) for r in realms}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
