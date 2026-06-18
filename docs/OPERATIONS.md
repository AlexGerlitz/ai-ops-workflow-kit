# Operations

## Runtime

```bash
docker compose up --build
```

Services:

- `api`: FastAPI application on port `8080`.
- `postgres`: PostgreSQL with pgvector enabled on port `5432`.
- `n8n`: workflow orchestration UI on port `5678`.

## Health

```bash
curl http://127.0.0.1:8080/health
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

## Offer Demo

Run the complete reviewer demo without Docker or API keys:

```bash
python scripts/run_offer_demo.py
```

The demo uses the synthetic files in `demo/` and proves:

- playbook ingestion;
- RAG query with source context;
- transcript webhook analysis;
- approval creation;
- approval transition;
- mock Bitrix24 integration event queued after approval.

See `docs/OFFER_DEMO.md` for the expected output shape.

## n8n Import

Import `infra/n8n/call-transcript-approval.json` into n8n, then set the API URL in the HTTP Request node.
The workflow accepts a transcript webhook, sends it to the FastAPI service, and returns the approval item.
