# Offer Demo

This is the fast reviewer path for the project.

The demo proves an end-to-end AI workflow automation scenario:

1. import an exported Google Drive sales playbook into the RAG store;
2. query the knowledge base with source context;
3. run deterministic RAG quality checks against expected sources, required terms, score floor, and citations;
4. expose the LLM provider boundary and local fallback state;
5. accept call-audio metadata through the n8n-facing webhook;
6. build a transcription provider contract and normalize the transcript;
7. score the lead and build a structured call analysis;
8. create a human approval item for the follow-up draft;
9. build a dry-run Telegram approval payload;
10. approve the item;
11. queue a dry-run Bitrix24 CRM handoff event;
12. build a dry-run Bitrix24 dispatch payload with idempotent outbox event state.

The point is not to show a prompt wrapper. The point is to show the production
boundary: n8n routes events, while the backend owns retrieval, scoring, state,
approval transitions, and integration contracts.

## One-Command Local Run

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_offer_demo.py
```

The script uses in-memory storage so a reviewer can run it without Docker or API keys.
Docker/PostgreSQL mode is still available through `docker compose up --build`.

The same workflow is available through the browser demo:

```text
http://127.0.0.1:8080/
```

The deployed browser demo is available at:

```text
https://saleops.duckdns.org/
```

The full public gate also runs tests and validates the demo output:

```bash
bash scripts/verify_public.sh
```

The live deployment smoke validates the public route and HTTPS callback base URL:

```bash
bash scripts/smoke_live_demo.sh
```

## Expected Shape

The output contains these sections:

| Section | What it proves |
| --- | --- |
| `runtime` | API booted and reported active storage, LLM provider state, deployment identity, workers, and counters. |
| `integrations` | Google Drive, Telegram, and Bitrix24 adapter readiness and public callback base URL. |
| `ingestion` | Sales playbook was chunked and stored. |
| `google_drive_import` | Exported Google Drive document text was normalized and imported into the RAG store. |
| `rag_context_sources` | Retrieval returned explicit source context. |
| `rag_quality` | Retrieval quality was checked through expected-source questions, required terms, score floor, and citations before LLM generation is trusted. |
| `transcription` | Call-audio metadata passed through the selected transcription boundary and returned normalized speaker segments. |
| `call_analysis` | Transcript was scored and converted into structured business action. |
| `approval` | Human-in-the-loop state transition happened before CRM handoff. |
| `telegram_approval` | Telegram approval payload and approve/reject callback contract were built in dry-run mode. |
| `crm_handoff` | A dry-run Bitrix24 adapter event was queued after approval, with idempotency key, attempt count, retry timing, and last error state. |
| `bitrix24_dispatch` | Bitrix24 dispatch payload was built in dry-run mode for the queued event and reports event state. |

Example high-level result:

```json
{
  "runtime": {
    "storage": "memory",
    "llm": {
      "selected_provider": "local",
      "supported_providers": ["local", "openai", "claude", "gemini"]
    }
  },
  "google_drive_import": {
    "adapter_key": "google_drive",
    "source": "gdrive://demo-sales-playbook",
    "chunks": 1
  },
  "rag_quality": {
    "ok": true,
    "passed": 2,
    "total": 2
  },
  "transcription": {
    "provider": "local_stub",
    "status": "dry_run",
    "audio_uri": "gdrive://demo-call-audio.mp3",
    "segments": [
      { "speaker": "manager", "text": "The client said the price may be expensive..." }
    ]
  },
  "call_analysis": {
    "score": 100,
    "risk_level": "medium",
    "objections": ["price sensitivity"],
    "next_action": "Send a concise recap and ask one direct qualification question."
  },
  "approval": {
    "status": "approved",
    "reviewer": "sales-lead"
  },
  "telegram_approval": {
    "adapter_key": "telegram.approval",
    "status": "dry_run"
  },
  "crm_handoff": {
    "adapter_key": "bitrix24.mock",
    "operation": "upsert_lead_follow_up",
    "status": "queued",
    "idempotency_key": "<sha256>",
    "attempt_count": 0
  },
  "bitrix24_dispatch": {
    "adapter_key": "bitrix24",
    "status": "dry_run",
    "event_status": "queued",
    "attempt_count": 0,
    "method": "crm.lead.update",
    "bitrix_request": {
      "id": "42",
      "fields": {
        "COMMENTS": "AI lead score, risk, summary, objections, and next task"
      },
      "params": { "REGISTER_SONET_EVENT": "Y" }
    }
  }
}
```

## Business Scenario

A sales manager keeps the playbook in Google Drive and finishes a call. n8n or another connector
exports the document text and sends it to the backend. The call recording metadata arrives from
telephony, Drive, or n8n. The backend converts it through the transcription boundary, searches the
playbook, extracts qualification signals, identifies objections, drafts a follow-up, and creates an
approval item. Only after a human reviewer approves the item does the backend queue the CRM handoff.

That maps directly to real AI automation work:

- call analysis;
- call-audio transcription boundary;
- Google Drive knowledge intake;
- RAG-backed generation;
- OpenAI/Claude/Gemini provider boundary with local fallback;
- lead scoring;
- Telegram-style approval;
- Bitrix/CRM integration;
- idempotent retry/dead-letter integration state;
- dry-run integration contracts before credentials are connected;
- opt-in Bitrix24 outbox worker for due CRM events;
- browser-visible control tower for a one-click review path;
- audit-friendly state transitions;
- repeatable local verification.

## Extension Points

- Connect Google Drive OAuth/service-account export before the import endpoint.
- Disable dry-run after adding Telegram Bot API and Bitrix24 webhook credentials.
- Replace deterministic local embeddings with OpenAI or another embedding API.
- Set `LLM_PROVIDER=openai`, `LLM_PROVIDER=claude`, or `LLM_PROVIDER=gemini` with the matching API key.
- Set `TRANSCRIPTION_PROVIDER=openai_whisper` or `TRANSCRIPTION_PROVIDER=deepgram` after adding audio storage and the matching provider key.
- Move the outbox worker into a separate process if the deployment needs independent scaling.
