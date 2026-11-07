# Job prompt and build log — JOB-7143 (before redaction)

*Fictional job record for the secret-redaction demo. Every key below is fake. In this public repository the fake keys
are stored as `<<FAKE:...>>` placeholders; the forge redaction tool expands them into obviously fake, correctly shaped
values before scanning, so no key-shaped string is ever committed.*

## Builder prompt (as typed in Agent Forge Home)

> Connect the price tracker to the new price feed and to our Slack alerts channel. Here's everything you need:
> price feed key PRICE_FEED_API_KEY=pf_live_demo_fake_key_000000 and the Google Maps key for store locations
> <<FAKE:google_api_key>>. For the summary use the OpenAI fallback key <<FAKE:openai_key>> if Gemini is busy.
> Slack bot token: <<FAKE:slack_token>>. The repo is private, use my token <<FAKE:github_token>>.

## Build log (excerpt)

```
2026-11-06T10:02:11Z INFO  connector=rest_client base_url=https://api.pricefeed.example/v2
2026-11-06T10:02:12Z DEBUG request headers={"Authorization": "Bearer <<FAKE:bearer_token>>"}
2026-11-06T10:02:12Z INFO  warehouse db=postgres://forge_app:FakeDemoPassw0rd@db.internal.example:5432/prices
2026-11-06T10:02:13Z DEBUG aws_access_key_id=<<FAKE:aws_access_key>> aws_secret_access_key=<<FAKE:aws_secret_key>>
2026-11-06T10:02:13Z DEBUG shopify token=<<FAKE:shopify_token>>
2026-11-06T10:02:14Z DEBUG oauth client_secret=<<FAKE:google_oauth_secret>>
2026-11-06T10:02:14Z DEBUG service account key:
<<FAKE:private_key>>
2026-11-06T10:02:15Z INFO  tests 8/8 passed; deploy to sandbox requested
```

## What should happen

The job prompt and the log are redacted before they are stored in the job log; the builder is told to rotate every
key that was pasted and to put secrets in the test pane (session) or Secret Manager (production) instead.
