"""Agent Forge tools: real static check, real secret redaction and the deterministic release gate."""
from agenthive.tools import forge as F

GOOD_AGENT = '''
import os

from google.adk.agents import Agent
from forge_connectors import tekmetric


def list_technicians(shop_id: int) -> dict:
    """List the active technicians of one shop from Tekmetric.

    Args:
        shop_id: Tekmetric shop id.
    """
    os.environ["TEKMETRIC_CLIENT_ID"], os.environ["TEKMETRIC_CLIENT_SECRET"]
    return {"status": "ok", "technicians": tekmetric.list_employees(shop_id)}


root_agent = Agent(name="bay_time", model=os.environ["FORGE_MODEL"], instruction="Report bay time.",
                   tools=[list_technicians])
'''
GOOD_TESTS = '''
from unittest import mock

import agent


def test_list_technicians_returns_ok():
    with mock.patch("agent.tekmetric.list_employees", return_value=[]):
        assert agent.list_technicians(1)["status"] == "ok"
'''


def test_static_check_passes_clean_code_and_issues_id():
    r = F.forge_static_check(GOOD_AGENT, GOOD_TESTS, agent="bay_time", version="v1",
                             required_secrets=["TEKMETRIC_CLIENT_ID", "TEKMETRIC_CLIENT_SECRET"])
    assert r["status"] == "ok" and r["passed"], r["errors"]
    assert r["static_check_id"].startswith("SC-") and r["executed"] is False


def test_static_check_flags_the_draft_doc():
    r = F.forge_static_check("forge_code_price_tracker_draft", agent="price_tracker", version="v2",
                             required_secrets=["PRICE_FEED_API_KEY"])
    rules = {(e["rule"], e["message"].split(":")[0]) for e in r["errors"]}
    assert not r["passed"] and r["static_check_id"] is None
    assert any(rule == "FS-02" for rule, _ in rules)                       # hard-coded key
    assert ("FS-01", "fetch_competitor_prices") in rules                   # no docstring / type hints
    assert any(w["rule"] == "FS-10" for w in r["warnings"])                # hard-coded model id
    assert r["tests"]["tools_without_test"] == ["email_big_moves"]


def test_static_check_never_executes_and_reports_syntax():
    r = F.forge_static_check("import os\nos.system('echo hi'\n")
    assert r["passed"] is False and r["errors"][0]["rule"] == "syntax"
    r = F.forge_static_check("import os\nfrom google.adk.agents import Agent\nos.system('rm -rf /')\n"
                             "root_agent = Agent(name='x', model='m', instruction='i')\n", "def test_x():\n    pass\n")
    assert any(e["rule"] == "safety" for e in r["errors"])


def test_redaction_finds_every_fake_key_and_hides_values():
    r = F.forge_redact_secrets("forge_job_prompt_leaky")
    expected = {"google_api_key", "openai_style_key", "slack_token", "github_token", "bearer_token", "password_in_url",
                "aws_access_key_id", "aws_secret_access_key", "shopify_token", "google_oauth_client_secret",
                "private_key_block", "generic_secret_assignment"}
    assert set(r["counts"]) == expected
    for value in F._fake_values().values():
        assert value not in r["redacted_text"]
    assert "FakeDemoPassw0rd" not in r["redacted_text"]
    assert "[REDACTED:google_api_key]" in r["redacted_text"]


def test_redaction_leaves_secret_names_and_references_alone():
    text = "secrets: [SHOPIFY_ADMIN_TOKEN]\ntoken = os.environ['SHOPIFY_ADMIN_TOKEN']\napi_key=SHOPIFY_ADMIN_TOKEN\n" \
           "client_secret = secret-manager://ridgeline/SHOPIFY_ADMIN_TOKEN"
    assert F.forge_redact_secrets(text)["clean"]


def test_release_gate_needs_a_passing_run():
    assert F.forge_deploy("employee_bay_time_tracker", "v3", "sandbox")["refused_by_gate"] == "tests"
    assert F.forge_run_tests("shopify_order_support_tracker", "v5")["status"] == "error"   # no static check yet
    sc = F._token("SC", "shopify_order_support_tracker", "v5", "pass")
    run = F.forge_run_tests("shopify_order_support_tracker", "v5", static_check_id=sc,
                            tests=["test_ltv_reads_amount_spent"])
    assert run["gate"] == "pass" and run["total"] == 14
    assert F.forge_deploy("shopify_order_support_tracker", "v5", "sandbox", test_run_id=sc)["deployed"] is False
    dep = F.forge_deploy("shopify_order_support_tracker", "v5", "sandbox", test_run_id=run["test_run_id"])
    assert dep["status"] == "ok" and dep["simulated"]
    assert all("secret-manager://" in v for v in dep["secret_references"].values())


def test_client_promotion_gates():
    own = F.forge_deploy("flight_lookup", "v1", "client", approved_by="lena.fischer@wursta.example")
    assert own["deployed"] is False and own["refused_by_gate"] == "approval"
    ok = F.forge_deploy("flight_lookup", "v1", "client", approved_by="elena.marsh@wursta.example")
    assert ok["status"] == "ok" and ok["target"] == "client"
    sc = F._token("SC", "summit_bay_time_tracker", "v1", "pass")
    run = F.forge_run_tests("summit_bay_time_tracker", "v1", client="Summit Tire & Auto", static_check_id=sc,
                            tests=["test_bay_minutes"], secrets=["TEKMETRIC_CLIENT_ID", "TEKMETRIC_CLIENT_SECRET"])
    assert run["gate"] == "pass"
    sbx = F.forge_deploy("summit_bay_time_tracker", "v1", "sandbox", client="summit_tire",
                         test_run_id=run["test_run_id"], secrets=["TEKMETRIC_CLIENT_ID"])
    assert sbx["status"] == "ok"
    prospect = F.forge_deploy("summit_bay_time_tracker", "v1", "client", client="summit_tire",
                              test_run_id=run["test_run_id"], approved_by="elena.marsh@wursta.example")
    assert prospect["refused_by_gate"] == "prospect"


def test_recorded_failures_and_blocked_tests():
    r = F.forge_run_tests("shopify_order_support_tracker", "v4")
    assert (r["passed"], r["failed"], r["gate"]) == (12, 1, "fail") and r["test_run_id"] is None
    assert "amountSpent" in r["failures"][0]["hint"]
    b = F.forge_run_tests("asset_audit_assistant")
    assert b["blocked"] == 3 and b["session_secrets"] == {"ASSET_PANDA_API_TOKEN": "missing"}


def test_spec_validation_and_access():
    v = F.forge_validate_spec({"name": "x", "client": "Ridgeline Outfitters", "secrets": ["not a name"]})
    assert not v["valid"]
    assert F.forge_check_access("jbaker@summittire.example", "Copperline Auto Care")["allowed"] is False
    findings = F.forge_access_review()["findings"]
    assert {f["user"] for f in findings if f["severity"] == "high"} == {
        "dev.contractor@freelance-studio.example", "pat.nguyen@northpass.example", "ops.lead@stonebridge.example"}
