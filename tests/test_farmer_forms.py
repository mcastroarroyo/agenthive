"""Farmer Desk: procedure menu and form filling (synthetic agriculture-ministry data)."""
import base64
import io
import json

from agenthive.tools import REGISTRY

procedures, fill = REGISTRY["gov_farm_procedures"], REGISTRY["gov_farm_fill_form"]
PHY = {"product": "café", "plot_id": "PLT-2024-104417", "quantity_kg": "3,000", "destination_country": "Alemania",
       "buyer": "Nordhafen Kaffee Import GmbH", "exit_point": "puerto de Port Alder", "shipment_date": "2026-12-04"}


class Ctx:
    def __init__(self):
        self.state = {}


def test_menu_and_detail():
    menu = procedures("", "es")["menu"]
    assert [m["code"] for m in menu] == ["PRD", "PLT", "PRG", "PHY", "MOV", "CER"]
    assert procedures("4", "en")["procedure"]["code"] == "PHY"
    assert procedures("mover ganado a la feria", "es")["procedure"]["code"] == "MOV"
    assert procedures("PLT", "en")["filled_by"] == "gov_farm_register_plot"


def test_form_ready_attaches_docx():
    from docx import Document
    ctx = Ctx()
    r = fill("PHY", "NPR-2024-018832", json.dumps(PHY), "es", tool_context=ctx)
    assert r["status"] == "ready" and r["fee_usd"] == 35 and r["file"].endswith(".docx")
    (f,) = ctx.state.values()
    text = "\n".join(p.text for p in Document(io.BytesIO(base64.b64decode(f["b64"]))).paragraphs)
    assert "SIMULADA" in text and "F-PHY-04" in text


def test_answers_object_and_prefill():
    r = fill("PHY", "Esteban Morales", {k: v for k, v in PHY.items() if k != "plot_id"}, "en")
    assert r["status"] == "ready"
    assert any(x["source"] == "registry" and x["value"].startswith("PLT-2024-104417") for x in r["form"])


def test_validation_and_missing():
    r = fill("PHY", "NPR-2024-018832", json.dumps({"product": "coffee", "quantity_kg": 9000, "shipment_date": "2026-11-07"}), "en")
    assert r["status"] == "incomplete"
    assert any("exceeds" in e for e in r["errors"]) and any("shipment_date" in e for e in r["errors"])
    assert {m["id"] for m in r["missing"]} >= {"destination_country", "buyer", "exit_point"}


def test_guards():
    assert fill("PRD", "VID 0412-7789-3", "", "en")["status"] == "error"            # already registered
    assert fill("PHY", "NPR-2026-031002", "", "en")["status"] == "error"            # identity not verified
    assert fill("PLT", "NPR-2024-018832", "", "en")["use"] == "gov_farm_register_plot"
    assert fill("PHY", "NPR-2024-018832", "not json", "en")["status"] == "error"


def test_answer_keys_are_mapped():
    bad = {"product_description": "Café verde", "plot": "PLT-2024-104417", "importer_name": "Nordhafen Kaffee Import GmbH",
           "quantity": "3,000 kg", "país de destino": "Alemania", "port_of_exit": "Puerto de Port Alder", "shipping_date": "2026-12-04"}
    assert fill("PHY", "NPR-2024-018832", bad, "es")["status"] == "ready"
    r = fill("PHY", "NPR-2024-018832", {"exporter_npr": "NPR-2024-018832"}, "en")
    assert r["unknown_fields"] == ["exporter_npr"] and "buyer" in r["field_ids"]
