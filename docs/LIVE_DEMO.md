# Live Demo

The public demo is deployed as a self-hosted FastAPI service behind Caddy/HAProxy.

Primary URL:

```text
https://saleops.duckdns.org/
```

Alias:

```text
https://leadscore.duckdns.org/
```

`saleops` is the main project name because the workflow covers more than a lead score:
RAG retrieval, transcript analysis, approval routing, and CRM handoff. `leadscore` is kept
as a narrower alias for the scoring surface.

## Browser Path

1. Open `https://saleops.duckdns.org/`.
2. Click `Run demo workflow`.
3. Verify the response shows a Google Drive import, high lead score, approved review state, dry-run Telegram payload,
   dry-run Bitrix24 dispatch, outbox drain count, and public worker state.

## Command-Line Smoke

```bash
bash scripts/smoke_live_demo.sh
bash scripts/smoke_live_demo.sh https://leadscore.duckdns.org
```

Expected output:

```text
live demo smoke passed
base_url=https://saleops.duckdns.org
callback_base_url=https://saleops.duckdns.org
version=0.2.0
git_sha=<deployed-sha>
score=100
google_drive=gdrive://demo-sales-playbook
approval=approved
telegram_callback=rejected
telegram=dry_run
bitrix24=dry_run
crm_event_status=queued
bitrix24_drain=<dry-run-count>
worker_active=False
```

The smoke check proves that the public edge route, FastAPI runtime, workflow endpoint,
approval callback base URL, runtime evidence, metrics endpoint, and integration dry-run
contracts are aligned. It also verifies that the browser UI exposes the current reviewer proof
labels: Google Drive import, Telegram callback approval, outbox drain, and worker state.
The `leadscore` alias intentionally keeps approval callbacks on the primary `saleops` URL.

## What Is Real

- The API is a real deployed service, not a static mock.
- The workflow runs through the same `/demo/run` endpoint used by local tests.
- The workflow imports exported Google Drive text into the same RAG store as direct document ingestion.
- The callback contract uses the public HTTPS base URL.
- The smoke check creates a synthetic approval and proves the Telegram callback webhook can reject it.
- Production deployments can enable `TELEGRAM_WEBHOOK_SECRET`; the public demo leaves it unset so smoke checks remain inspectable.
- `/runtime` exposes deployed version, Git SHA, public callback base URL, integration readiness, and counters.
- `/metrics` exposes Prometheus-style runtime and workflow counters.
- Google Drive, Telegram, and Bitrix24 remain in dry-run mode until credentials are configured.
- Bitrix24 dry-run leaves CRM events queued; production mode records idempotency, attempts, `next_retry_at`, `last_error`, and `dead_letter`.
- The live smoke also calls `POST /integrations/bitrix24/drain` to prove the worker-style queue drain surface.
- `GET /runtime` shows the Bitrix24 outbox worker is disabled in the public dry-run demo.

## Local Fallback

If the public VPS is unavailable, run the same proof locally:

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
```
