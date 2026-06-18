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
BITRIX24_ADAPTER_KEY = "bitrix24"


def integration_runtime(config: Settings) -> IntegrationRuntimeOut:
    return IntegrationRuntimeOut(
        public_base_url=config.public_base_url,
        capabilities=[
            IntegrationCapabilityOut(
                adapter_key=TELEGRAM_ADAPTER_KEY,
                configured=bool(config.telegram_bot_token and config.telegram_approval_chat_id),
                dry_run=config.telegram_dry_run,
                required_env=["TELEGRAM_BOT_TOKEN", "TELEGRAM_APPROVAL_CHAT_ID"],
                notes="Sends approval cards to Telegram. Dry-run returns the exact outgoing payload.",
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


def build_bitrix24_handoff_payload(event: IntegrationEventOut) -> dict[str, object]:
    method = "crm.lead.update" if event.operation == "upsert_lead_follow_up" else event.operation
    return {
        "method": method,
        "event_id": str(event.id),
        "source_approval_id": str(event.source_approval_id) if event.source_approval_id else None,
        "crm_update": event.payload,
    }


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
        response = httpx.post(method_url, json=payload["crm_update"], timeout=10)
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
