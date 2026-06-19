from __future__ import annotations

from urllib.parse import urljoin

import httpx

from app.schemas import (
    ApprovalOut,
    IntegrationCapabilityOut,
    IntegrationDispatchOut,
    IntegrationDispatchStatus,
    IntegrationEventOut,
    IntegrationRuntimeOut,
)
from app.settings import Settings


TELEGRAM_ADAPTER_KEY = "telegram.approval"
GOOGLE_DRIVE_ADAPTER_KEY = "google_drive"
BITRIX24_ADAPTER_KEY = "bitrix24"


def integration_runtime(config: Settings) -> IntegrationRuntimeOut:
    return IntegrationRuntimeOut(
        public_base_url=config.public_base_url,
        capabilities=[
            IntegrationCapabilityOut(
                adapter_key=TELEGRAM_ADAPTER_KEY,
                configured=bool(config.telegram_bot_token and config.telegram_approval_chat_id),
                dry_run=config.telegram_dry_run,
                webhook_secret_configured=bool(config.telegram_webhook_secret),
                required_env=["TELEGRAM_BOT_TOKEN", "TELEGRAM_APPROVAL_CHAT_ID"],
                notes=(
                    "Sends approval cards to Telegram. Dry-run returns the exact outgoing payload. "
                    "TELEGRAM_WEBHOOK_SECRET optionally verifies callback webhooks."
                ),
            ),
            IntegrationCapabilityOut(
                adapter_key=GOOGLE_DRIVE_ADAPTER_KEY,
                configured=bool(config.google_drive_credentials_json),
                dry_run=config.google_drive_dry_run,
                required_env=["GOOGLE_DRIVE_CREDENTIALS_JSON"],
                notes=(
                    "Imports exported Google Drive document text into the RAG pipeline. "
                    "Dry-run/public mode accepts normalized text from n8n or a connector without storing credentials."
                ),
            ),
            IntegrationCapabilityOut(
                adapter_key=BITRIX24_ADAPTER_KEY,
                configured=bool(config.bitrix24_webhook_url),
                dry_run=config.bitrix24_dry_run,
                required_env=["BITRIX24_WEBHOOK_URL"],
                notes="Dispatches approved CRM handoff events through a Bitrix24 incoming webhook.",
            ),
        ],
    )


def build_telegram_approval_payload(approval: ApprovalOut, public_base_url: str) -> dict[str, object]:
    approve_url = _join_url(public_base_url, f"/approvals/{approval.id}/approve")
    reject_url = _join_url(public_base_url, f"/approvals/{approval.id}/reject")
    webhook_url = _join_url(public_base_url, "/webhooks/telegram/approval")
    text = (
        f"<b>{approval.title}</b>\n\n"
        f"{approval.draft}\n\n"
        f"Approval ID: <code>{approval.id}</code>"
    )
    return {
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "Approve", "callback_data": f"approve:{approval.id}"},
                    {"text": "Reject", "callback_data": f"reject:{approval.id}"},
                ]
            ]
        },
        "callback_contract": {
            "approve": {"method": "POST", "url": approve_url},
            "reject": {"method": "POST", "url": reject_url},
            "telegram_webhook": {"method": "POST", "url": webhook_url},
        },
    }


def dispatch_telegram_approval(approval: ApprovalOut, config: Settings) -> IntegrationDispatchOut:
    payload = build_telegram_approval_payload(approval, config.public_base_url)
    if config.telegram_dry_run:
        return IntegrationDispatchOut(
            adapter_key=TELEGRAM_ADAPTER_KEY,
            operation="send_approval_message",
            status=IntegrationDispatchStatus.dry_run,
            payload=payload,
            detail="Dry-run mode is enabled; Telegram API was not called.",
        )
    if not config.telegram_bot_token or not config.telegram_approval_chat_id:
        return IntegrationDispatchOut(
            adapter_key=TELEGRAM_ADAPTER_KEY,
            operation="send_approval_message",
            status=IntegrationDispatchStatus.not_configured,
            payload=payload,
            detail="Telegram token or approval chat id is not configured.",
        )

    request_payload = {
        **payload,
        "chat_id": config.telegram_approval_chat_id,
    }
    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    try:
        response = httpx.post(url, json=request_payload, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return IntegrationDispatchOut(
            adapter_key=TELEGRAM_ADAPTER_KEY,
            operation="send_approval_message",
            status=IntegrationDispatchStatus.failed,
            payload=payload,
            detail=f"Telegram API call failed: {exc.__class__.__name__}",
        )

    body = response.json()
    message_id = body.get("result", {}).get("message_id")
    return IntegrationDispatchOut(
        adapter_key=TELEGRAM_ADAPTER_KEY,
        operation="send_approval_message",
        status=IntegrationDispatchStatus.sent,
        payload=payload,
        detail=f"Telegram message sent: {message_id}",
    )


def answer_telegram_callback(callback_query_id: str, text: str, config: Settings) -> None:
    if config.telegram_dry_run or not config.telegram_bot_token:
        return

    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/answerCallbackQuery"
    try:
        response = httpx.post(
            url,
            json={"callback_query_id": callback_query_id, "text": text[:200]},
            timeout=5,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        # The approval is already processed by this point; do not fail the webhook
        # only because Telegram could not clear the client-side button spinner.
        return


def build_bitrix24_handoff_payload(event: IntegrationEventOut) -> dict[str, object]:
    method = "crm.lead.update" if event.operation == "upsert_lead_follow_up" else event.operation
    bitrix_request = (
        build_bitrix24_lead_update_request(event.payload)
        if method == "crm.lead.update"
        else event.payload
    )
    return {
        "method": method,
        "event_id": str(event.id),
        "source_approval_id": str(event.source_approval_id) if event.source_approval_id else None,
        "crm_update": event.payload,
        "bitrix_request": bitrix_request,
    }


def build_bitrix24_lead_update_request(crm_update: dict[str, object]) -> dict[str, object]:
    task = crm_update.get("task")
    task_description = ""
    if isinstance(task, dict):
        title = str(task.get("title") or "").strip()
        description = str(task.get("description") or "").strip()
        if title or description:
            task_description = f"\nNext task: {title} - {description}".strip()

    objections = crm_update.get("objections")
    objection_text = ", ".join(str(item) for item in objections) if isinstance(objections, list) else ""
    missing_signals = ""
    fields_payload = crm_update.get("fields")
    if isinstance(fields_payload, dict):
        raw_missing = fields_payload.get("AI Missing Signals")
        if isinstance(raw_missing, list):
            missing_signals = ", ".join(str(item) for item in raw_missing)

    comment_parts = [
        f"AI lead score: {crm_update.get('lead_score')}",
        f"AI risk level: {crm_update.get('risk_level')}",
        f"Target stage: {crm_update.get('target_stage')}",
        f"Call id: {crm_update.get('call_id')}",
        f"Summary: {crm_update.get('comment')}",
    ]
    if objection_text:
        comment_parts.append(f"Objections: {objection_text}")
    if missing_signals:
        comment_parts.append(f"Missing signals: {missing_signals}")
    if task_description:
        comment_parts.append(task_description)

    return {
        "id": bitrix24_lead_id(crm_update.get("customer_id")),
        "fields": {
            "COMMENTS": "\n".join(part for part in comment_parts if part and not part.endswith("None")),
        },
        "params": {"REGISTER_SONET_EVENT": "Y"},
    }


def bitrix24_lead_id(customer_id: object) -> str:
    value = str(customer_id or "").strip()
    if value.upper().startswith("LEAD-"):
        candidate = value.rsplit("-", 1)[-1]
        if candidate.isdigit():
            return candidate
    return value


def dispatch_bitrix24_event(event: IntegrationEventOut, config: Settings) -> IntegrationDispatchOut:
    payload = build_bitrix24_handoff_payload(event)
    if config.bitrix24_dry_run:
        return IntegrationDispatchOut(
            adapter_key=BITRIX24_ADAPTER_KEY,
            operation=event.operation,
            status=IntegrationDispatchStatus.dry_run,
            payload=payload,
            detail="Dry-run mode is enabled; Bitrix24 webhook was not called.",
        )
    if not config.bitrix24_webhook_url:
        return IntegrationDispatchOut(
            adapter_key=BITRIX24_ADAPTER_KEY,
            operation=event.operation,
            status=IntegrationDispatchStatus.not_configured,
            payload=payload,
            detail="Bitrix24 webhook URL is not configured.",
        )

    method_url = _join_url(config.bitrix24_webhook_url, f"/{payload['method']}.json")
    try:
        response = httpx.post(method_url, json=payload["bitrix_request"], timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return IntegrationDispatchOut(
            adapter_key=BITRIX24_ADAPTER_KEY,
            operation=event.operation,
            status=IntegrationDispatchStatus.failed,
            payload=payload,
            detail=f"Bitrix24 webhook call failed: {exc.__class__.__name__}",
        )

    return IntegrationDispatchOut(
        adapter_key=BITRIX24_ADAPTER_KEY,
        operation=event.operation,
        status=IntegrationDispatchStatus.sent,
        payload=payload,
        detail="Bitrix24 webhook call completed.",
    )


def _join_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
