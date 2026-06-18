# Reviewer Checklist

This checklist is the fastest way to verify that AI Ops Workflow Kit is more than a prompt wrapper.

## 1. Run The Live Reviewer Snapshot

For a full public acceptance pass across live API, live smoke, GitHub Actions, Pages, and public PDF,
run:

```bash
python3 scripts/reviewer_acceptance_report.py
```

Read: [Reviewer Acceptance Report](./REVIEWER_ACCEPTANCE_REPORT.md).

```bash
python3 scripts/reviewer_snapshot.py
```

Expected result:

```text
technical reviewer snapshot passed
```

The snapshot checks the public deployment, `/runtime`, `/llm/runtime`, `/integrations/runtime`,
`/metrics`, and `/demo/run`. It summarizes the deployed Git SHA, selected LLM provider, supported
providers, Google Drive/RAG source, score, approval state, Telegram dry-run state, Bitrix24 dry-run
state, CRM idempotency key, worker state, and metrics availability.

Read: [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md).
For the current CI/live-smoke/local-gate status, read
[Public Proof Status](./PUBLIC_PROOF_STATUS.md).

## 2. Regenerate The Evidence Pack

```bash
python3 scripts/capture_reviewer_evidence.py
```

This writes a sanitized live snapshot to `docs/evidence/` and redacts only the per-run CRM
idempotency key. Read: [Reviewer Evidence Pack](./REVIEWER_EVIDENCE_PACK.md).

## 3. Run The Public Gate

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
```

Expected result:

```text
31 passed
public verification passed
```

The gate runs the test suite, runs the offer demo, parses the demo output, and asserts that the
workflow produced:

- RAG context sources;
- Google Drive import into the same RAG store;
- OpenAI, Claude/Anthropic, Gemini, and local fallback provider boundary;
- transcript score;
- structured call analysis;
- approved human review item;
- dry-run Telegram approval payload;
- Telegram callback webhook for inline approve/reject decisions;
- optional Telegram webhook secret verification;
- queued `bitrix24.mock` CRM handoff.
- dry-run Bitrix24 dispatch payload.
- Bitrix24 idempotency, retry scheduling, drain, opt-in worker, and dead-letter state for failed production dispatches.
- runtime identity and metrics surface.

## 4. Run The Production Readiness Drill

```bash
python3 scripts/production_readiness_drill.py
```

This checks webhook-secret rejection, Bitrix24 retry/dead-letter state, retry scheduling, CRM
handoff idempotency, and worker dry-run guard without external credentials. Read:
[Production Readiness Drill](./PRODUCTION_READINESS_DRILL.md).

## 5. Run The Credentialed Sandbox Preflight

```bash
python3 scripts/credentialed_sandbox_preflight.py
```

Public mode records skipped/no-secret evidence. With Telegram and Bitrix24 sandbox credentials, run:

```bash
python3 scripts/credentialed_sandbox_preflight.py --require-credentials
```

If only one sandbox account is available, run a target-specific read-only check instead:

```bash
python3 scripts/credentialed_sandbox_preflight.py --require-target telegram
python3 scripts/credentialed_sandbox_preflight.py --require-target bitrix24
```

This performs read-only Telegram and Bitrix24 checks without printing tokens or writing CRM records.
Read: [Credentialed Sandbox Preflight](./CREDENTIALED_SANDBOX_PREFLIGHT.md).

When repository secrets are configured, the owner can also run the manual
`Credentialed Sandbox Preflight` GitHub Actions workflow with target `telegram`, `bitrix24`, or
`all`. The workflow uploads sanitized evidence artifacts and runs a secret leakage check before
finishing.

## 6. Inspect The Offer Demo

```bash
python3 scripts/run_offer_demo.py
```

The demo does not require Docker or external API keys. It uses deterministic local embeddings and
in-memory storage so the reviewer can inspect the behavior quickly.

Read: [Offer Demo](./OFFER_DEMO.md).

## 7. Inspect The Live Demo

Open:

- Sales Ops Control Tower: https://saleops.duckdns.org/
- Lead score alias: https://leadscore.duckdns.org/

Or run:

```bash
python3 scripts/reviewer_snapshot.py
bash scripts/smoke_live_demo.sh
```

Read: [Live Demo](./LIVE_DEMO.md).

## 8. Inspect The Browser Demo Locally

Run the API and open the one-click demo surface:

```bash
docker compose up --build
```

Then open:

- Sales Ops Control Tower: http://127.0.0.1:8080/

## 9. Inspect The Runtime Boundary

Run the Docker stack when you want to inspect the API with PostgreSQL/pgvector and n8n:

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- API health: http://127.0.0.1:8080/health
- Runtime evidence: http://127.0.0.1:8080/runtime
- LLM provider evidence: http://127.0.0.1:8080/llm/runtime
- Metrics: http://127.0.0.1:8080/metrics
- FastAPI docs: http://127.0.0.1:8080/docs
- n8n UI: http://127.0.0.1:5678

## 10. Review The Engineering Decisions

| File | What to check |
| --- | --- |
| [README](../README.md) | Reviewer snapshot, API surface, repository layout, and checks. |
| [Public Proof Status](./PUBLIC_PROOF_STATUS.md) | Current CI, live smoke, local public gate, Pages route, and public demo boundary. |
| [Reviewer Acceptance Report](./REVIEWER_ACCEPTANCE_REPORT.md) | One-command public acceptance check across live API, live smoke, GitHub Actions, Pages, and PDF. |
| [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md) | Live snapshot, architecture decisions, failure modes, production rollout checklist, and public demo boundary. |
| [Reviewer Evidence Pack](./REVIEWER_EVIDENCE_PACK.md) | Committed sanitized live evidence and regeneration command. |
| [Production Readiness Drill](./PRODUCTION_READINESS_DRILL.md) | Failure-mode evidence for auth, retry/dead-letter, drain scheduling, idempotency, and worker guard. |
| [Credentialed Sandbox Preflight](./CREDENTIALED_SANDBOX_PREFLIGHT.md) | Read-only real-credential boundary for Telegram and Bitrix24 sandbox checks. |
| [Owner-run Sandbox Workflow](../.github/workflows/credentialed-sandbox-preflight.yml) | Manual GitHub Actions path for sanitized Telegram/Bitrix24 sandbox evidence from repository secrets. |
| [Evidence Map](./EVIDENCE_MAP.md) | Requirement-by-requirement proof map for AI automation roles. |
| [Role Requirements Map](./ROLE_REQUIREMENTS_MAP.md) | Vacancy-style AI automation requirements mapped to files, endpoints, commands, and production boundaries. |
| [Live Demo](./LIVE_DEMO.md) | Public deployment URL and public smoke checks. |
| [Architecture](./ARCHITECTURE.md) | FastAPI/n8n/PostgreSQL/LLM boundaries and state ownership. |
| [Operations](./OPERATIONS.md) | Local runtime, health checks, smoke test, logs, and handoff. |
| [n8n Approval Flow](./N8N_APPROVAL_FLOW.md) | How importable transcript and Google Drive workflow routing, Telegram payloads, and approval callbacks connect. |
| [Integration Skeleton](./INTEGRATION_SKELETON.md) | How Google Drive, Telegram, and Bitrix24 dry-run contracts become real credentials later. |
| [Tests](../tests/) | Deterministic coverage for retrieval, scoring, approval, CRM handoff, idempotency, drain, background worker, and integration retry/dead-letter behavior. |

## 11. What This Proves

- AI workflow logic is backend-owned and testable.
- The project has a browser-visible demo, not only README claims.
- n8n is used as orchestration glue and connector routing, not as hidden domain logic.
- LLM/RAG behavior has deterministic local fallbacks and OpenAI/Claude/Gemini provider contracts for repeatable review.
- CRM mutation is queued only after explicit human approval.
- CRM dispatch failures become retry/dead-letter state with `next_retry_at`, not invisible log-only errors.
- Retry timing, webhook auth, idempotency, and worker dry-run guard are captured by a deterministic drill.
- Real Telegram and Bitrix24 credentials can be checked through a read-only, token-redacted preflight.
- Google Drive, Telegram, and Bitrix24 adapters expose dry-run contracts before credentials are connected.
- Telegram inline callbacks have a backend endpoint that applies approve/reject state transitions.
- Production Telegram callbacks can be protected with `X-Telegram-Bot-Api-Secret-Token`.
- Runtime and metrics endpoints expose deploy identity and workflow counters.
- `/llm/runtime` exposes provider state without exposing secrets.
- Runtime exposes whether the Bitrix24 outbox worker is enabled and active.
- The project has a public verification command and CI gate.
