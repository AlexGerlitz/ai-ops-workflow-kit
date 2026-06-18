# Operations

## Runtime

```bash
docker compose up --build
```

Services:

- `api`: FastAPI application on port `8080`.
- `postgres`: PostgreSQL with pgvector enabled on port `5432`.
- `n8n`: workflow orchestration UI on port `5678`.

Browser demo:

```text
http://127.0.0.1:8080/
```

Public demo:

```text
https://saleops.duckdns.org/
https://leadscore.duckdns.org/
```

## Health

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/runtime
curl http://127.0.0.1:8080/llm/runtime
curl http://127.0.0.1:8080/metrics
```

Expected response:

```json
{
  "ok": true,
  "storage": "postgres",
  "embedding_dim": 64
}
```

If `DATABASE_URL` is unset, the API uses in-memory storage. That mode is useful for tests and contract
development, not for production.

## Runtime Evidence

`GET /runtime` reports:

- application version;
- Git SHA supplied at deploy time;
- deploy environment;
- storage mode;
- public callback base URL;
- selected LLM provider and configured provider names;
- integration readiness;
- worker readiness;
- workflow counters.

`GET /llm/runtime` reports the provider boundary in more detail: requested provider, selected
provider, supported providers, required env vars, and whether each provider is configured. It does
not return API keys.

`GET /metrics` exposes the same runtime identity and workflow counters in Prometheus text format.
This is intentionally dependency-light so it works in local review, Docker, and the public demo.

## LLM Providers

The default mode is deterministic and review-safe:

```env
LLM_PROVIDER=auto
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
```

With no provider key configured, `/query` uses the local extractive fallback from retrieved context.
When a key is configured, `LLM_PROVIDER=auto` selects providers in this order: OpenAI, Claude/Anthropic,
Gemini. A provider can also be forced explicitly:

```env
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini

LLM_PROVIDER=claude
ANTHROPIC_MODEL=claude-sonnet-4-20250514

LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
```

Provider API keys stay in deployment configuration and are never committed.

## Logs

```bash
docker compose logs -f api
docker compose logs -f postgres
docker compose logs -f n8n
```

## Smoke Test

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS -X POST http://127.0.0.1:8080/documents \
  -H 'content-type: application/json' \
  -d '{"source":"smoke","text":"AI workflow smoke test with approval routing.","metadata":{"env":"local"}}'
curl -fsS -X POST http://127.0.0.1:8080/query \
  -H 'content-type: application/json' \
  -d '{"question":"What routing is mentioned?","top_k":2}'
```

## Telegram Callback Check

Create or inspect an approval item, then send Telegram-style callback data:

```bash
curl -fsS -X POST http://127.0.0.1:8080/webhooks/telegram/approval \
  -H 'content-type: application/json' \
  -d '{"callback_query":{"id":"cb-smoke","from":{"id":7001,"username":"saleslead"},"data":"reject:{approval_id}"}}'
```

Production Telegram webhook setup:

```bash
TELEGRAM_BOT_TOKEN=... \
PUBLIC_BASE_URL=https://saleops.duckdns.org \
TELEGRAM_WEBHOOK_SECRET=... \
bash scripts/configure_telegram_webhook.sh
```

Do not commit Telegram tokens or webhook secrets. Keep them in server environment, a secret manager,
or deployment runtime variables.

## Offer Demo

Run the complete reviewer demo without Docker or API keys:

```bash
python3 scripts/run_offer_demo.py
```

The demo uses synthetic sales payloads and proves:

- playbook ingestion;
- RAG query with source context;
- LLM provider runtime and local fallback state;
- transcript webhook analysis;
- approval creation;
- approval transition;
- mock Bitrix24 integration event queued after approval.
- Bitrix24 dispatch state with idempotency, attempts, retry timing, last error, and dead-letter handling.
- browser-visible control tower at `/`.

See `docs/OFFER_DEMO.md` for the expected output shape.

## Integration Skeleton

The public callback base URL is:

```env
PUBLIC_BASE_URL=https://saleops.duckdns.org
```

Google Drive, Telegram, and Bitrix24 are dry-run by default. This keeps public verification deterministic while
showing the exact payloads that will be sent after credentials are configured:

```bash
curl http://127.0.0.1:8080/integrations/runtime
curl -X POST http://127.0.0.1:8080/integrations/google-drive/import \
  -H "content-type: application/json" \
  -d '{"file_id":"ops-playbook","name":"Ops playbook","mime_type":"application/vnd.google-apps.document","text":"Approval workflows need RAG context and explicit handoff state.","metadata":{"source":"ops"}}'
curl -X POST http://127.0.0.1:8080/approvals/{approval_id}/notify/telegram
curl -X POST http://127.0.0.1:8080/integration-events/{event_id}/dispatch/bitrix24
curl -X POST http://127.0.0.1:8080/integrations/bitrix24/drain
```

When `BITRIX24_DRY_RUN=false`, the Bitrix24 dispatch endpoint records each send attempt on the
integration event. Failed attempts increment `attempt_count`, update `last_error`, set `next_retry_at`,
and move the event to `dead_letter` after `INTEGRATION_MAX_ATTEMPTS`.

To run the outbox drain in the API process, explicitly enable the worker:

```env
INTEGRATION_WORKER_ENABLED=true
BITRIX24_DRY_RUN=false
INTEGRATION_WORKER_INTERVAL_SECONDS=60
INTEGRATION_WORKER_BATCH_SIZE=10
```

The worker is intentionally disabled in the public demo and will not start while Bitrix24 dry-run is
enabled. Its state is visible in `GET /runtime` under `workers.bitrix24_outbox`.

See `docs/INTEGRATION_SKELETON.md`.

## Public Verification Gate

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
```

The gate runs tests, runs the offer demo, and validates that Google Drive import, RAG retrieval,
LLM provider boundary, approval, mock Bitrix24 handoff, runtime metrics, and outbox dispatch state
are present in the output.

## Live Deployment Smoke

```bash
python3 scripts/capture_reviewer_evidence.py
python3 scripts/reviewer_snapshot.py
bash scripts/smoke_live_demo.sh
bash scripts/smoke_live_demo.sh https://leadscore.duckdns.org
```

This verifies the public Caddy/HAProxy route, browser demo HTML, `/demo/run`, Google Drive import,
approval callback base URL, Telegram callback webhook, runtime evidence, metrics endpoint, and
dry-run integration contracts. It also checks `/llm/runtime`.

For a concise live evidence report that reviewers can paste into an evaluation note:

```bash
python3 scripts/reviewer_snapshot.py --json
```

For committed reviewer evidence, regenerate the sanitized pack:

```bash
python3 scripts/capture_reviewer_evidence.py
```

This writes `docs/evidence/reviewer-snapshot.sanitized.json` and
`docs/evidence/reviewer-snapshot.txt`. The capture script validates the live workflow before writing
the files.

## n8n Import

Import one of these workflows into n8n, then set the API URL in the HTTP Request nodes:

```text
infra/n8n/call-transcript-approval.json
infra/n8n/google-drive-sales-ops-approval.json
```

The transcript workflow accepts a transcript webhook, sends it to the FastAPI service, and returns
the approval item. The Google Drive workflow first sends exported Drive text to
`POST /integrations/google-drive/import`, then sends the transcript event to
`POST /webhooks/n8n/call-transcript`.

See `docs/N8N_APPROVAL_FLOW.md` for the webhook payload, Telegram payload boundary, approval callback,
and CRM handoff rule.
