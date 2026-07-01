# Live Demo

The public demo is deployed as a self-hosted FastAPI service behind Caddy/HAProxy.
Treat it as a live runtime check, not the only evidence route. If the VPS edge is unavailable,
start with [Public Evidence Status](./PUBLIC_PROOF_STATUS.md), the committed evidence under
`docs/evidence/`, and the local public gate.

Primary URL:

```text
https://saleops.duckdns.org/
```

Alias:

```text
https://leadscore.duckdns.org/
```

`saleops` is the main project name because the workflow covers more than a lead score:
RAG retrieval, call-audio transcription, transcript analysis, approval routing, and CRM handoff. `leadscore` is kept
as a narrower alias for the scoring surface.

## Browser Path

1. Confirm `https://saleops.duckdns.org/` is reachable, then open it.
2. Click `Run demo workflow`.
3. Verify the response shows Document/CRM knowledge intake, LLM provider boundary, transcription status,
   high lead score, approved review state, dry-run Telegram payload, dry-run Bitrix24 dispatch,
   outbox drain count, and public worker state.
4. Upload an `.m4a`, `.mp3`, or `.wav` call recording in the live audio panel when a Deepgram key
   is configured. The browser path sends the temporary audio file through `POST /demo/audio/upload`,
   returns the transcript, lead score, pending approval, and a Telegram approval dispatch. On an
   owner deployment this can send to the real bot; Bitrix24 remains dry-run unless explicitly
   credentialed.

## Command-Line Smoke

```bash
python3 scripts/capture_reviewer_evidence.py
python3 scripts/reviewer_snapshot.py
bash scripts/smoke_live_demo.sh
bash scripts/smoke_live_demo.sh https://leadscore.duckdns.org
```

Expected output:

```text
technical reviewer snapshot passed
base_url=https://saleops.duckdns.org
llm=local requested=auto fallback=True
```

Smoke output:

```text
live demo smoke passed
base_url=https://saleops.duckdns.org
callback_base_url=https://saleops.duckdns.org
version=0.2.0
git_sha=<deployed-sha>
storage=postgres
llm=local
score=100
google_drive=gdrive://demo-sales-playbook
rag_eval=2/2
transcription=local_stub:dry_run
approval=approved
telegram_callback=rejected
telegram=dry_run
bitrix24=dry_run
crm_event_status=queued
bitrix24_drain=<dry-run-count>
worker_active=False
```

The smoke check verifies that the public edge route, FastAPI runtime, PostgreSQL/pgvector storage mode, workflow endpoint,
approval callback base URL, LLM provider runtime, transcription boundary, runtime evidence, metrics endpoint,
and integration dry-run contracts are aligned. It also verifies that the browser UI exposes the current
reviewer evidence labels: Google Drive import, call audio transcription, OpenAI/Claude/Gemini provider boundary,
Telegram callback approval, live audio upload, outbox drain, and worker state.
The `leadscore` alias intentionally keeps approval callbacks on the primary `saleops` URL.

For the complete reviewer route, read [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md).
For committed live evidence, read [Reviewer Evidence Pack](./REVIEWER_EVIDENCE_PACK.md).

## What Is Real

- The API is a real deployed service, not a static mock.
- The live production route uses PostgreSQL/pgvector storage; local tests can still use memory mode for deterministic review.
- The workflow runs through the same `/demo/run` endpoint used by local tests.
- The workflow imports exported Google Drive text into the same RAG store as direct document ingestion.
- The workflow accepts call-audio metadata and returns normalized transcript segments before scoring.
- `POST /demo/audio/upload` accepts a temporary browser-uploaded recording and runs the same
  transcription -> transcript analysis -> approval path with live STT when a provider key is configured.
- The callback contract uses the public HTTPS base URL.
- The smoke check creates a synthetic approval and verifies the Telegram callback webhook can reject it.
- `/llm/runtime` exposes OpenAI, Claude/Anthropic, Gemini, and local fallback state without returning secrets.
- `/transcription/runtime` exposes local fixture, OpenAI Whisper, and Deepgram provider state without returning secrets.
- Production deployments can enable `TELEGRAM_WEBHOOK_SECRET`; the public demo leaves it unset so smoke checks remain inspectable.
- `/runtime` exposes deployed version, Git SHA, public callback base URL, integration readiness, and counters.
- `/metrics` exposes Prometheus-style runtime and workflow counters.
- Google Drive and Bitrix24 remain in dry-run mode until credentials are configured.
- `/demo/run` keeps Telegram dry-run for public safety; operator-triggered approval messages can use
  the real Telegram bot and are documented in [Live Owner Evidence](./LIVE_OWNER_PROOF.md).
- The one-click synthetic smoke remains dry-run/local-fixture for deterministic review; the upload panel
  can run live Deepgram transcription when `DEEPGRAM_API_KEY` is configured.
- Bitrix24 dry-run leaves CRM events queued; production mode records idempotency, attempts, `next_retry_at`, `last_error`, and `dead_letter`.
- The live smoke also calls `POST /integrations/bitrix24/drain` to verify the worker-style queue drain surface.
- `GET /runtime` shows the Bitrix24 outbox worker is disabled in the public dry-run demo.
- `docs/evidence/live-postgres-persistence.txt` records a live API restart check where a RAG document
  remained retrievable from PostgreSQL/pgvector after the API container restarted.

## Local Fallback

If the public VPS is unavailable, run the same evidence path locally:

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
```

The stable reviewer route is [Public Evidence Status](./PUBLIC_PROOF_STATUS.md); the public runtime
URLs are useful when the deployment edge is online, but they are not the only evidence path.
