# Privacy Boundary

This project now has a small regulated-workflow proof slice: transcript PII is redacted before it
enters public workflow evidence.

## What Is Redacted

The public demo and transcript webhook redact these categories:

- email addresses;
- phone-like values;
- payment-card-like values;
- IBAN-like values.

The demo fixture intentionally includes an email and an international-format phone number so reviewers can
verify that the raw values do not appear in public output.

## Where Redaction Happens

`POST /webhooks/n8n/call-transcript` redacts the transcript before:

- RAG ingestion;
- approval draft/context creation;
- CRM handoff payload construction;
- Bitrix24 dry-run request output;
- demo JSON and reviewer snapshot output;
- public logs or metrics evidence.

`POST /webhooks/n8n/call-audio` reuses the same transcript path after transcription and redacts the
transcription response returned by the public API.

## How To Verify

Run:

```bash
bash scripts/verify_public.sh
```

The public gate checks that the synthetic demo output:

- reports `privacy.redacted=true`;
- reports `raw_text_stored=false`;
- includes replacement counts for email and phone;
- contains `[redacted-email]` and `[redacted-phone]`;
- does not contain the raw demo email or raw phone number.

Focused tests:

```bash
python3 -m pytest -q tests/test_api.py -k privacy
```

## Boundary

This is not a full compliance framework. It is a concrete proof that the backend owns a privacy
boundary before RAG, approval, CRM handoff, and public evidence. Future production work should add
tenant-specific retention policies, access controls, data export/delete workflows, and audit review.
