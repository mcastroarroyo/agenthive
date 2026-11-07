# Generated code — Price Tracker v2 draft (Ridgeline Outfitters)

*Fictional first draft produced by a forge build before review. It has deliberate problems for the static-check demo.
The key below is a fake placeholder value, not a real credential.*

## agent.py

```python
import os

import requests
from google.adk.agents import Agent

PRICE_API_KEY = "demo-price-feed-key-000000000000"
FEED_URL = "https://api.pricefeed.example/v2/prices"


def fetch_competitor_prices(skus):
    r = requests.get(FEED_URL, params={"sku": ",".join(skus)},
                     headers={"Authorization": "Bearer " + PRICE_API_KEY})
    return r.json()


def append_price_rows(rows: list[dict]) -> dict:
    """Append rows."""
    from forge_connectors import google_sheets
    google_sheets.append_rows(os.environ["PRICE_SHEET_ID"], "Prices", rows)
    return {"status": "ok", "rows": len(rows)}


def email_big_moves(moves: list[dict], to: str) -> dict:
    """Draft an email to the buyer listing competitor price moves above the threshold (Gmail draft, never sent).

    Args:
        moves: Price moves with sku, competitor, old_price, new_price and pct_change.
        to: Buyer email address.

    Returns:
        Draft id and the number of moves included.
    """
    from forge_connectors import gmail
    body = "\n".join(f"{m['sku']}: {m['competitor']} {m['pct_change']:+.1f}%" for m in moves)
    draft = gmail.create_draft(to=to, subject="Competitor price moves", body=body)
    return {"status": "ok", "draft_id": draft["id"], "moves": len(moves)}


root_agent = Agent(
    name="price_tracker",
    model="gemini-3.5-flash",
    instruction="Every morning fetch competitor prices for the top 40 SKUs, log them, and draft an email to the "
                "buyer about moves larger than 5%.",
    tools=[fetch_competitor_prices, append_price_rows, email_big_moves],
)
```

## test_agent.py

```python
from unittest import mock

import agent


def test_fetch_prices_parses_feed():
    with mock.patch("agent.requests.get") as get:
        get.return_value.json.return_value = {"prices": [{"sku": "RG-TENT-2P", "price": 249.0}]}
        assert agent.fetch_competitor_prices(["RG-TENT-2P"])["prices"][0]["price"] == 249.0


def test_append_price_rows_counts_rows():
    with mock.patch("forge_connectors.google_sheets.append_rows"):
        assert agent.append_price_rows([{"sku": "RG-TENT-2P"}])["rows"] == 1
```
