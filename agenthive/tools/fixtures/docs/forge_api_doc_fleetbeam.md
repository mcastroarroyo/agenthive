# FleetBeam Delivery API v2 — developer reference (excerpt)

*Fictional vendor documentation linked by a builder for the Connector Smith demo. FleetBeam is not a real company.*

## Overview

FleetBeam tracks parcel deliveries for online stores across regional carriers. The REST API returns JSON; all
timestamps are UTC in ISO 8601.

- Production base URL: https://api.fleetbeam.example/v2
- Sandbox base URL: https://sandbox.fleetbeam.example/v2

## Authentication

Every request must send your API key in the `X-FleetBeam-Key` header. Keys are created per store in the FleetBeam
dashboard (Settings → API keys). Sandbox and production keys are different. Never put the key in a query string.

## Endpoints

| Method and path | Description |
|---|---|
| GET /shipments | List shipments. Filters: `status`, `updated_since`, `order_ref`, `cursor`, `limit` |
| GET /shipments/{shipment_id} | One shipment with carrier, tracking number, promised date and current status |
| GET /shipments/{shipment_id}/events | Scan events for a shipment, newest first |
| GET /exceptions | Delivery exceptions. Filters: `since`, `type`, `resolved`, `cursor`, `limit` |
| POST /exceptions/{exception_id}/acknowledge | Mark an exception as seen by the store |
| POST /webhooks | Register a webhook URL for `exception.created` and `shipment.delivered` |

Exception `type` values: `address_issue`, `damaged`, `delayed_weather`, `carrier_delay`, `refused`, `lost`.
Each exception carries `shipment_id`, `order_ref` (the store's order number), `customer_email`, `type`,
`created_at` and `carrier_message`.

## Pagination

List endpoints are cursor-paginated. Pass `limit` (default 50, maximum 200). When more results exist the response
contains `next_cursor`; send it back as `cursor` until `next_cursor` is null.

## Rate limits

120 requests per minute per API key. Over the limit the API returns HTTP 429 with a `Retry-After` header (seconds).

## Errors

Errors return `{"error": {"code": "...", "message": "..."}}`.

| Status | Meaning |
|---|---|
| 400 | invalid filter or body |
| 401 | missing or invalid API key |
| 404 | unknown shipment or exception |
| 409 | exception already acknowledged |
| 429 | rate limit exceeded — wait for Retry-After |
| 500, 503 | transient server error — retry with backoff |

## Webhooks

Webhook payloads are signed with HMAC-SHA256 in the `X-FleetBeam-Signature` header using your webhook secret.
