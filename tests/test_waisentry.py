"""WAISentry tools: determinism, zero-PII consistency, playbook guardrails and BigQuery seed agreement (offline)."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

from agenthive.tools import waisentry as W
from agenthive.tools._base import FIXTURES

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"\b(?:USR|EXT|FIL|DEV|MSG)-[0-9A-F]{4}\b")


def _seed():
    spec = importlib.util.spec_from_file_location("bq_smb_security", ROOT / "deploy" / "seed" / "bq_smb_security.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SEED = _seed()
TABLES = SEED.tables()


def test_token_scheme_matches_seed():
    for kind, value in [("user", "maya.singh@kitewing.example"), ("device", "jpetit-win"), ("file", "Vendor bank details 2026.xlsx")]:
        assert W.token(kind, value) == SEED.token(kind, value)


def test_fixture_tokens_resolve_in_tenant():
    vocab = W._vocab()
    for name in ["sentry_telemetry", "sentry_incidents", "sentry_identity", "sentry_saas", "sentry_fleet"]:
        text = (FIXTURES / f"{name}.json").read_text()
        unknown = sorted(set(TOKEN.findall(text)) - set(vocab))
        assert not unknown, f"{name}: tokens not in the tenant vocabulary: {unknown}"


def test_fixtures_are_fictional():
    for p in FIXTURES.glob("sentry_*.json"):
        text = p.read_text()
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
            assert ip.startswith(("192.0.2.", "198.51.100.", "203.0.113.")), f"{p.name}: non-documentation IP {ip}"
        for dom in re.findall(r"@([a-z0-9.-]+)", text):
            assert dom.endswith(".example"), f"{p.name}: non-.example domain {dom}"


def test_triage_is_deterministic():
    a, b = W.sentry_triage_batch("TB-1101-0200"), W.sentry_triage_batch("sunday")
    assert a == b and a["status"] == "ok"
    assert a["alerts_raised"] == 7 and a["incidents"][0]["incident"] == "INC-1101-01"
    assert all(x["actor"].startswith("USR-") for x in a["alerts"])
    assert W.sentry_triage_batch("TB-1106-0900")["alerts_raised"] == 2


def test_seed_matches_triage_scores():
    rows = {r["event_id"]: r for r in TABLES["sentry_events"]}
    assert len(rows) == len(TABLES["sentry_events"])
    for bid in ("TB-1101-0200", "TB-1028-1400", "TB-1106-0900"):
        for a in W.sentry_triage_batch(bid)["alerts"]:
            assert rows[a["event"]]["triage_score"] == a["score"]
            assert rows[a["event"]]["verdict"] == "incident"
    inc = {r["incident_id"]: r for r in TABLES["sentry_incidents"]}
    assert set(inc) == {i["id"] for i in W._incidents()}
    assert inc["INC-1101-01"]["active_containment_seconds"] == 29


def test_seed_volumes_match_saas_summary():
    saas = json.loads((FIXTURES / "sentry_saas.json").read_text())["alerts"]
    dns = [r for r in TABLES["sentry_ingest_daily"] if r["source"] == "dnsfilter"]
    assert sum(r["raw_records"] for r in dns) == saas["30"]["dnsfilter"]["queries"]
    assert sum(r["raw_records"] for r in dns if r["day"] >= "2026-10-31") == saas["7"]["dnsfilter"]["queries"]


def test_containment_timings_and_guardrails():
    r = W.sentry_quarantine_drive("INC-1101-01")
    assert r["executed"] and r["completed"] == "02:08:21" and r["time_to_contain_s"] == 29
    assert W.sentry_end_sessions("INC-1101-01", "Maya Singh")["target"] == "USR-CFA4"
    assert W.sentry_revoke_oauth_app("INC-1101-01", "Slack")["refused"]
    assert W.sentry_suspend_account("INC-1101-01", "USR-CFA4", 24)["refused"]
    assert W.sentry_end_sessions("INC-1106-01", "USR-FDB1")["refused"]           # medium severity
    assert W.sentry_suspend_account("INC-1101-01", "noah.kim")["refused"]        # protected admin
    verdicts = {c["action"]: c["verdict"] for c in W.sentry_playbook_check(
        ["end her sessions", "wipe the laptop", "remove the forwarding filter", "quarantine the Drive files"])["checks"]}
    assert verdicts == {"end her sessions": "pre-approved", "wipe the laptop": "not pre-approved — escalate",
                        "remove the forwarding filter": "not pre-approved — escalate",
                        "quarantine the Drive files": "pre-approved"}


def test_zero_pii_reidentification_needs_tenant():
    assert W.sentry_reidentify(["USR-CFA4"])["refused"]
    r = W.sentry_reidentify(["USR-CFA4"], in_tenant=True, requester="Noah Kim", reason="INC-1101-01")
    assert not r["refused"] and "Maya Singh" in r["resolved"][0]["identity"]
    t = W.sentry_tokenize(doc_key="sentry_email_vendor_bank_change")
    assert "Maya" not in t["tokenised_text"] and "8800" not in t["tokenised_text"]
    assert t["body_signals_extracted_in_tenant"]["asks_to_change_bank_details"]


def test_bec_and_posture_numbers():
    b = W.sentry_bec_check(doc_key="sentry_email_vendor_bank_change")
    assert b["score"] >= 75 and b["amount_at_risk_usd"] == 48600 and b["linked_incident"] == "INC-1101-01"
    cmp_ = W.sentry_posture_review("compare")
    assert (cmp_["baseline_score"], cmp_["current_score"]) == (20, 75)
    assert "20 -> 75" in (FIXTURES / "sentry_compliance.json").read_text()


@pytest.mark.parametrize("q,status", [("Do you retain security logs for a year?", "Yes"),
                                      ("Do you keep immutable backups?", "Client to answer")])
def test_questionnaire_answers(q, status):
    assert W.sentry_answer_questionnaire([q])["answers"][0]["status"] == status
