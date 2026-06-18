# Reviewer Checklist

This checklist is the fastest way to verify that AI Ops Workflow Kit is more than a prompt wrapper.

## 1. Run The Public Gate

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
```

Expected result:

```text
8 passed
public verification passed
```

The gate runs the test suite, runs the offer demo, parses the demo output, and asserts that the
workflow produced:

- RAG context sources;
- transcript score;
- structured call analysis;
- approved human review item;
- queued `bitrix24.mock` CRM handoff.

## 2. Inspect The Offer Demo

```bash
python3 scripts/run_offer_demo.py
```

The demo does not require Docker or external API keys. It uses deterministic local embeddings and
in-memory storage so the reviewer can inspect the behavior quickly.

Read: [Offer Demo](./OFFER_DEMO.md).

## 3. Inspect The Runtime Boundary

Run the Docker stack when you want to inspect the API with PostgreSQL/pgvector and n8n:

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- API health: http://127.0.0.1:8080/health
- FastAPI docs: http://127.0.0.1:8080/docs
- n8n UI: http://127.0.0.1:5678

## 4. Review The Engineering Decisions

| File | What to check |
| --- | --- |
| [README](../README.md) | Reviewer snapshot, API surface, repository layout, and checks. |
| [Architecture](./ARCHITECTURE.md) | FastAPI/n8n/PostgreSQL/LLM boundaries and state ownership. |
| [Operations](./OPERATIONS.md) | Local runtime, health checks, smoke test, logs, and handoff. |
| [n8n Approval Flow](./N8N_APPROVAL_FLOW.md) | How webhook routing, Telegram payloads, and approval callbacks connect. |
| [Tests](../tests/) | Deterministic coverage for retrieval, scoring, approval, and CRM handoff. |

## 5. What This Proves

- AI workflow logic is backend-owned and testable.
- n8n is used as orchestration glue, not as hidden domain logic.
- LLM/RAG behavior has deterministic local fallbacks for repeatable review.
- CRM mutation is queued only after explicit human approval.
- The project has a public verification command and CI gate.
