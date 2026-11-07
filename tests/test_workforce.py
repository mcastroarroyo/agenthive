"""Agent Workforce tools: the real document renderer, brand learning and checks, claim extraction and the estimator."""
import base64
import io
import json

import pytest

from agenthive.tools import workforce as W
from agenthive.tools._base import fixture


class FakeContext:
    """Stands in for ADK's ToolContext: the tools only use `.state`."""

    def __init__(self):
        self.state = {}


MD = """# Proposal for Alderbrook Home Services
Kitewing FieldOps Growth with Route Optimizer

## Executive summary
Alderbrook wants **a real plan** before the spring peak.

- First-year total: $145,542.08
- Go-live before 2027-03-01

## Investment
| Item | Amount |
|---|---|
| Subscription, year 1 (ACV) | $130,042.08 |
| Standard implementation | $12,000 |

### Terms
Net 30.

## Next steps
1. Discovery follow-up on 2026-11-10
2. Demo in the week of 2026-11-16
"""


def _file(ctx, result):
    assert result["status"] == "ok", result
    entry = ctx.state[f"hive_file:{result['file_id']}"]
    assert set(entry) == {"name", "mime", "size", "b64"}
    data = base64.b64decode(entry["b64"])
    assert len(data) == entry["size"] == result["size"] < W.MAX_FILE_BYTES
    assert entry["name"] == result["name"]
    assert "b64" not in json.dumps(result)                       # the bytes never go back to the model
    return entry, data


def test_render_docx_reopens_with_brand_styles():
    from docx import Document

    ctx = FakeContext()
    r = W.wf_render_document(title="", output_format="docx", markdown=MD, prepared_for="Alderbrook Home Services",
                             job_id="WFJ-1", confidential=True, tool_context=ctx)
    entry, data = _file(ctx, r)
    assert entry["name"] == "proposal-for-alderbrook-home-services.docx" and entry["mime"] == W.MIME["docx"]
    doc = Document(io.BytesIO(data))
    texts = [p.text for p in doc.paragraphs]
    assert "KITEWING" in texts and "Proposal for Alderbrook Home Services" in texts
    assert "Kitewing FieldOps Growth with Route Optimizer" in texts                # subtitle from the intro line
    assert [p.text for p in doc.paragraphs if p.style.name == "Heading 1"] == ["Executive summary", "Investment",
                                                                              "Next steps"]
    h1 = doc.styles["Heading 1"].font
    assert h1.name == "Montserrat" and str(h1.color.rgb) == "14365D"
    assert doc.styles["Normal"].font.name == "Open Sans"
    assert doc.tables[0].rows[0].cells[0].text == "Item" and doc.tables[0].rows[1].cells[1].text == "$130,042.08"
    assert "Confidential" in doc.sections[0].footer.paragraphs[0].text
    assert r["outline"] == ["Executive summary", "Investment", "Next steps"] and r["pages_est"] >= 2


def test_render_pptx_reopens_with_title_and_content_slides():
    from pptx import Presentation

    ctx = FakeContext()
    sections = [{"heading": f"Slide {i}", "bullets": [f"Point {j}" for j in range(4)]} for i in range(3)]
    sections.append({"heading": "Investment", "body": "Prices as quoted.",
                     "table": [["Item", "Amount"], ["Growth", "$115,920"]], "notes": "Pause for questions."})
    r = W.wf_render_document(title="Pitch deck", output_format="pptx", subtitle="For Alderbrook", sections=sections,
                             tool_context=ctx)
    _, data = _file(ctx, r)
    prs = Presentation(io.BytesIO(data))
    assert r["slides"] == len(prs.slides) == 5
    title_texts = [sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame]
    assert "Pitch deck" in title_texts and "For Alderbrook" in title_texts
    last = prs.slides[4]
    assert any(sh.has_table for sh in last.shapes)
    assert last.notes_slide.notes_text_frame.text == "Pause for questions."


def test_render_pptx_splits_long_sections():
    ctx = FakeContext()
    r = W.wf_render_document(title="Long", output_format="pptx",
                             sections=[{"heading": "Many points", "bullets": [f"p{i}" for i in range(14)]}],
                             tool_context=ctx)
    assert r["slides"] == 1 + 3                                    # title + 6 + 6 + 2 bullets


def test_render_xlsx_reopens_with_typed_cells_and_about_sheet():
    from openpyxl import load_workbook

    ctx = FakeContext()
    sheets = [{"name": "Calendar", "rows": [["Date", "Channel", "Hook"], ["2026-12-01", "linkedin", "86% first fix"],
                                            ["2026-12-02", "instagram", "Meet the team"]]},
              {"name": "Pillar mix", "rows": [{"Pillar": "Customer outcomes", "Target %": 40, "Planned": 7}]}]
    r = W.wf_render_document(title="December calendar", output_format="xlsx", sheets=sheets, tool_context=ctx)
    _, data = _file(ctx, r)
    wb = load_workbook(io.BytesIO(data))
    assert wb.sheetnames == ["Calendar", "Pillar mix", "About"] and r["sheets"] == 3
    ws = wb["Calendar"]
    assert ws["A1"].value == "Date" and ws["A1"].fill.fgColor.rgb.endswith("14365D")
    assert ws.freeze_panes == "A2" and ws.auto_filter.ref == "A1:C3"
    assert ws["A2"].value.isoformat().startswith("2026-12-01")
    assert wb["Pillar mix"]["B2"].value == 40


def test_render_xlsx_from_markdown_tables_md_csv_and_pdf_fallback():
    ctx = FakeContext()
    r = W.wf_render_document(title="T", output_format="xlsx", markdown=MD, tool_context=ctx)
    assert r["status"] == "ok" and r["outline"] == ["Investment"]
    r = W.wf_render_document(title="T", output_format="csv", markdown=MD, tool_context=ctx)
    _, data = _file(ctx, r)
    assert data.decode().splitlines()[0] == "Item,Amount"
    r = W.wf_render_document(title="T", output_format="md", markdown=MD, tool_context=ctx)
    _, data = _file(ctx, r)
    assert data.decode().startswith("# T") and "## Investment" in data.decode()
    r = W.wf_render_document(title="T", output_format="pdf", markdown=MD, tool_context=ctx)
    assert r["format"] == "docx" and r["note"]


def test_render_is_deterministic_versioned_and_validates():
    ctx = FakeContext()
    a = W.wf_render_document(title="SOP", markdown=MD, tool_context=ctx)
    b = W.wf_render_document(title="SOP", markdown=MD, tool_context=ctx)
    v2 = W.wf_render_document(title="SOP", markdown=MD, version=2, tool_context=ctx)
    assert a["file_id"] == b["file_id"] != v2["file_id"] and v2["name"] == "sop-v2.docx"
    assert len([k for k in ctx.state if k.startswith("hive_file:")]) == 2
    assert W.wf_render_document(title="x", output_format="exe", markdown=MD, tool_context=ctx)["status"] == "error"
    assert W.wf_render_document(title="x", markdown="", tool_context=ctx)["status"] == "error"
    assert W.wf_render_document(title="x", markdown=MD, tool_context=object())["status"] == "error"
    assert W.wf_render_document(title="x", markdown=MD, brand="Nobody Inc", tool_context=ctx)["status"] == "error"


def test_render_house_style_and_learned_brand():
    ctx = FakeContext()
    house = W.wf_render_document(title="Plain", markdown=MD, brand="house", tool_context=ctx)
    assert house["brand_id"] == "BRD-HOUSE"
    guidelines = fixture("wf_brand_profiles")  # noqa: F841 — make sure the library loads
    text = W.doc_text("wf_kitewing_brand_guidelines").replace("Kitewing Software", "Bramble Bakery").replace(
        "#14365D", "#7A1F3D")
    learned = W.wf_brand_learn(text, tool_context=ctx)
    assert learned["status"] == "ok" and learned["name"] == "Bramble Bakery"
    r = W.wf_render_document(title="Menu", markdown=MD, brand=learned["brand_id"], tool_context=ctx)
    assert r["brand"] == "Bramble Bakery"


def test_brand_learn_reproduces_the_stored_kitewing_profile():
    ctx = FakeContext()
    r = W.wf_brand_learn("wf_kitewing_brand_guidelines", tool_context=ctx)
    stored = next(p for p in fixture("wf_brand_profiles")["profiles"] if p["name"] == "Kitewing Software")
    assert r["brand_id"] == stored["brand_id"] == W._brand_id("Kitewing Software")
    assert r["library"].startswith("matches the stored profile")
    assert r["colours"]["primary"] == "Dispatch Navy #14365D" and r["fonts"]["heading"].startswith("Montserrat")
    assert r["banned_words"] == len(stored["banned_words"]) == 19
    assert r["coverage"]["missing"] == []
    learned = ctx.state[f"wf_brand:{r['brand_id']}"]
    assert learned["fact_rules"] == stored["fact_rules"]          # curated fact rules survive a re-learn


def test_brand_check_flags_the_planted_draft():
    r = W.wf_brand_check("wf_draft_press_release")
    found = {(b["rule"], b["found"]) for b in r["blocking"]}
    for word in ("revolutionary", "leverage", "seamlessly", "cutting-edge", "game-changer"):
        assert ("banned word", word) in found
    assert ("product name", "Kitewing AI") in found and ("product name", "route optimizer") in found
    assert ("customer naming", "Harbor & Pine Mechanical") in found
    assert ("customer naming", "Bluefin Elevator Services") in found
    assert ("prospect named", "Alderbrook Home Services") in found
    assert any(b["rule"] == "claims policy" and "40%" in b["found"] for b in r["blocking"])
    rules = {w["rule"] for w in r["warnings"]}
    assert {"competitor named", "punctuation", "emojis", "US spelling", "sentence-case headings"} <= rules
    assert r["passed"] is False and r["score"] < 50


def test_brand_check_respects_audience_and_passes_clean_copy():
    clean = ("Greystone Facilities Group now sends invoices in 2 days instead of 9. Kitewing FieldOps keeps every "
             "branch on one dispatch board, and Route Optimizer re-sequences the day when a job is cancelled.")
    r = W.wf_brand_check(clean)
    assert r["passed"] and r["blocking"] == []
    proposal = "Kitewing FieldOps for Alderbrook Home Services: first-year total $145,542.08."
    assert W.wf_brand_check(proposal, audience="client")["blocking"] == []
    assert W.wf_brand_check(proposal, audience="public")["blocking"][0]["rule"] == "prospect named"
    post = "86% first-time fix at Greystone Facilities Group!! #FieldService #HVAC #Kitewing #AI"
    r = W.wf_brand_check(post, channel="linkedin")
    assert any(b["rule"] == "hashtags" for b in r["blocking"])


def test_extract_claims_checks_approved_facts():
    r = W.wf_extract_claims("wf_draft_press_release")
    topics = {c.get("topic") for c in r["claims"] if c["status"] == "contradicts"}
    assert {"Spanish-language answers", "AI model", "Customer count", "Security certification",
            "Greystone Facilities Group results"} <= topics
    assert any(c["status"] == "restricted" and "Alderbrook" in c["claim"] for c in r["claims"])
    web = [c for c in r["claims"] if c["status"] == "check_web"]
    assert web and "Bureau of Labor Statistics" in web[0]["claim"] and web[0]["query"]
    ok_text = ("Greystone Facilities Group raised first-time fix from 71% to 86%. Kitewing holds a SOC 2 Type II "
               "report. About 170 active customers run on Kitewing FieldOps.")
    r = W.wf_extract_claims(ok_text)
    assert r["counts"].get("contradicts", 0) == 0 and r["counts"]["matches"] >= 2
    addressee = "Alderbrook Home Services runs 140 technicians on DispatchPro 7 today."
    assert W.wf_extract_claims(addressee, audience="client")["counts"].get("restricted", 0) == 0
    assert W.wf_extract_claims(addressee, audience="public")["counts"]["restricted"] == 1


def test_estimator_scopes_briefs_and_prices_tiers():
    r = W.wf_estimate_job("wf_brief_proposal_alderbrook")
    assert [(d["kind"], d["format"]) for d in r["deliverables"]] == [("proposal", "docx")]
    assert r["recommended_tier"] == "P2" and r["billable_agents"] == 1
    assert {e["tier"]: e["reserve_credits"] for e in r["estimate"]} == {"P1": 9.0, "P2": 6.0, "P3": 3.0}
    assert r["credits"]["balance"] == 120 and r["credits"]["enough"]
    assert "Illustrative pricing, not final" in r["pricing"]
    three = W.wf_estimate_job("a job", deliverables=["blog_post", "content_calendar"])
    assert three["billable_agents"] == 3
    assert {e["tier"]: e["reserve_credits"] for e in three["estimate"]} == {"P1": 27.0, "P2": 18.0, "P3": 9.0}
    assert W.wf_estimate_job("wf_brief_gtm_assist_spanish")["recommended_tier"] == "P1"
    assert W.wf_estimate_job("wf_brief_blog_peak_season")["recommended_tier"] == "P3"
    deck = W.wf_estimate_job("Turn our Alderbrook proposal into a pitch deck")
    assert [(d["kind"], d["format"]) for d in deck["deliverables"]] == [("pitch_deck", "pptx")]
    multi = W.wf_estimate_job("An SEO audit of our website plus 3 blog post briefs, no rush")
    assert {d["kind"]: d["quantity"] for d in multi["deliverables"]} == {"seo_audit": 1, "blog_brief": 3}
    assert multi["recommended_tier"] == "P3"
    assert W.wf_estimate_job("hello there, can you help me")["status"] == "error"


def test_marketplace_has_70_agents_in_10_departments():
    mk = fixture("wf_marketplace")
    assert len(mk["departments"]) == 10 and sum(d["agents"] for d in mk["departments"]) == mk["total_agents"] == 70
    r = W.wf_marketplace(need="We need a LinkedIn content calendar and a client proposal")
    hire = [h["agent_id"] for rec in r["recommendations"] for h in (rec["hire_in_this_hive"] or [])]
    assert {"wf_social_planner", "wf_proposal_writer"} <= set(hire)
    assert W.wf_marketplace(department="Media")["experimental"] is True
    assert W.wf_marketplace(need="build us a chatbot for our website")["not_what_we_do"]


def test_specialist_helpers():
    audit = W.wf_seo_audit()
    assert audit["issues"][0]["severity"] == "critical" and audit["issues"][0]["page"] == "/assist"
    assert any("duplicate title" in i["issue"] for i in audit["issues"]) and audit["quick_wins"]
    slots = W.wf_social_slots("2026-12-01", 4)
    assert slots["total"] == 18 and {s["date"] for s in slots["skipped"]} == {"2026-12-24", "2026-12-25"}
    assert any("Greystone" in s.get("moment", "") for s in slots["slots"])
    assert all(abs(m["planned_pct"] - m["target_pct"]) <= 5 for m in slots["pillar_mix"])
    assert W.wf_social_slots("2026-01-01")["status"] == "error"
    sop = W.wf_sop_check([{"step": "Send the handoff form", "owner": "Account Executive", "done_when": "submitted"},
                          {"step": "Sales Engineer reviews integrations as needed", "owner": "SE / AE"}],
                         roles=["Account Executive", "Finance"])
    assert {i["step"] for i in sop["issues"]} == {2} and sop["roles_without_steps"] == ["Finance"]
    size = W.wf_market_size([{"name": "HVAC", "accounts": 1000, "annual_value": 10000, "serviceable_pct": 50,
                              "obtainable_pct": 10, "source": "https://example.org"}])
    assert size["total"] == {"tam": 10_000_000, "sam": 5_000_000, "som": 500_000}
    check = W.wf_seo_check_draft("reduce technician overtime", "How to reduce technician overtime",
                                 "x" * 130, "## One\n## Two\n## Three\n" + "reduce technician overtime " * 3
                                 + "word " * 120)
    assert check["status"] == "ok" and 0 <= check["score"] <= 100
    brief = W.wf_seo_check_draft("reduce technician overtime", "How to reduce technician overtime in peak season",
                                 "Peak season does not have to mean overtime. A practical plan to reduce technician "
                                 "overtime with better scheduling and maintenance visits.",
                                 "## Why overtime spikes\n## How to reduce technician overtime\n## Checklist\n"
                                 "Call to action: download the spring rush checklist." + " outline" * 30,
                                 draft_type="brief")
    assert brief["draft_type"] == "brief" and brief["readability"] is None and not any(
        "density" in f or "links" in f for f in brief["fixes"])


@pytest.mark.parametrize("kind", sorted(fixture("wf_templates")["templates"]))
def test_templates_reference_hive_specialists(kind):
    ids = {s["agent_id"] for s in fixture("wf_marketplace")["hive_specialists"]}
    t = W.wf_deliverable_template(kind)
    assert t["status"] == "ok" and set(t["specialists"]) <= ids and t["default_format"] in t["formats"]
