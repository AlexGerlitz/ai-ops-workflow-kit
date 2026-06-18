from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.schemas import RetrievedContext

LOCAL_PROVIDER = "local"
OPENAI_PROVIDER = "openai"
CLAUDE_PROVIDER = "claude"
GEMINI_PROVIDER = "gemini"
AUTO_PROVIDER = "auto"
SUPPORTED_PROVIDERS = (LOCAL_PROVIDER, OPENAI_PROVIDER, CLAUDE_PROVIDER, GEMINI_PROVIDER)
REMOTE_PROVIDERS = (OPENAI_PROVIDER, CLAUDE_PROVIDER, GEMINI_PROVIDER)
PROVIDER_ALIASES = {
    "anthropic": CLAUDE_PROVIDER,
    "google": GEMINI_PROVIDER,
}


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    api_key: str | None
    model: str
    required_env: str | None

    @property
    def configured(self) -> bool:
        return self.provider == LOCAL_PROVIDER or bool(self.api_key)


class LLMClient:
    def __init__(
        self,
        *,
        provider: str = AUTO_PROVIDER,
        openai_api_key: str | None = None,
        openai_model: str = "gpt-4.1-mini",
        anthropic_api_key: str | None = None,
        anthropic_model: str = "claude-sonnet-4-20250514",
        gemini_api_key: str | None = None,
        gemini_model: str = "gemini-2.5-flash",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.requested_provider = self._normalize_provider(provider)
        self.timeout_seconds = timeout_seconds
        self.providers = {
            LOCAL_PROVIDER: ProviderConfig(LOCAL_PROVIDER, None, "extractive", None),
            OPENAI_PROVIDER: ProviderConfig(
                OPENAI_PROVIDER, openai_api_key, openai_model, "OPENAI_API_KEY"
            ),
            CLAUDE_PROVIDER: ProviderConfig(
                CLAUDE_PROVIDER, anthropic_api_key, anthropic_model, "ANTHROPIC_API_KEY"
            ),
            GEMINI_PROVIDER: ProviderConfig(
                GEMINI_PROVIDER, gemini_api_key, gemini_model, "GEMINI_API_KEY"
            ),
        }

    async def answer(self, question: str, contexts: list[RetrievedContext]) -> str:
        if not contexts:
            return "No relevant context was found."

        selected_provider = self.selected_provider
        if selected_provider == OPENAI_PROVIDER:
            return await self._openai_answer(question, contexts)
        if selected_provider == CLAUDE_PROVIDER:
            return await self._claude_answer(question, contexts)
        if selected_provider == GEMINI_PROVIDER:
            return await self._gemini_answer(question, contexts)
        return self._extractive_answer(question, contexts)

    @property
    def selected_provider(self) -> str:
        remote_provider = self._selected_remote_provider()
        return remote_provider or LOCAL_PROVIDER

    def runtime(self) -> dict[str, Any]:
        selected = self.selected_provider
        providers = []
        for provider in SUPPORTED_PROVIDERS:
            config = self.providers[provider]
            providers.append(
                {
                    "provider": provider,
                    "model": config.model,
                    "configured": config.configured,
                    "selected": selected == provider,
                    "required_env": [config.required_env] if config.required_env else [],
                    "notes": self._provider_note(provider),
                }
            )
        return {
            "requested_provider": self.requested_provider,
            "selected_provider": selected,
            "fallback": selected == LOCAL_PROVIDER and self.requested_provider != LOCAL_PROVIDER,
            "configured_providers": [
                provider for provider in REMOTE_PROVIDERS if self.providers[provider].configured
            ],
            "supported_providers": list(SUPPORTED_PROVIDERS),
            "providers": providers,
        }

    def _normalize_provider(self, provider: str) -> str:
        normalized = provider.strip().lower()
        normalized = PROVIDER_ALIASES.get(normalized, normalized)
        if normalized in (AUTO_PROVIDER, *SUPPORTED_PROVIDERS):
            return normalized
        return AUTO_PROVIDER

    def _selected_remote_provider(self) -> str | None:
        if self.requested_provider == AUTO_PROVIDER:
            for provider in REMOTE_PROVIDERS:
                if self.providers[provider].configured:
                    return provider
            return None
        if self.requested_provider in REMOTE_PROVIDERS:
            config = self.providers[self.requested_provider]
            return config.provider if config.configured else None
        return None

    def _provider_note(self, provider: str) -> str:
        if provider == LOCAL_PROVIDER:
            return "Deterministic extractive fallback for repeatable public review."
        config = self.providers[provider]
        if config.configured:
            return "Configured by environment; API calls stay behind the LLM boundary."
        return f"Set {config.required_env} to enable this provider."

    def _extractive_answer(self, question: str, contexts: list[RetrievedContext]) -> str:
        joined = " ".join(context.text for context in contexts[:2])
        return f"Draft answer for: {question}\n\nContext: {joined[:1200]}"

    async def _openai_answer(self, question: str, contexts: list[RetrievedContext]) -> str:
        config = self.providers[OPENAI_PROVIDER]
        payload = build_openai_payload(question, contexts, config.model)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"authorization": f"Bearer {config.api_key}"},
                json=payload,
            )
            response.raise_for_status()
        return parse_openai_response(response.json())

    async def _claude_answer(self, question: str, contexts: list[RetrievedContext]) -> str:
        config = self.providers[CLAUDE_PROVIDER]
        payload = build_claude_payload(question, contexts, config.model)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": config.api_key or "",
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        return parse_claude_response(response.json())

    async def _gemini_answer(self, question: str, contexts: list[RetrievedContext]) -> str:
        config = self.providers[GEMINI_PROVIDER]
        payload = build_gemini_payload(question, contexts, config.model)
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{config.model}:generateContent"
        )
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                url,
                params={"key": config.api_key},
                headers={"content-type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
        return parse_gemini_response(response.json())


def build_prompt(question: str, contexts: list[RetrievedContext]) -> str:
    context_text = "\n\n".join(
        f"Source: {context.source}\n{context.text}" for context in contexts
    )
    return f"Question: {question}\n\nContext:\n{context_text}"


def build_openai_payload(
    question: str, contexts: list[RetrievedContext], model: str
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer from the provided context. If context is insufficient, "
                    "say what is missing."
                ),
            },
            {"role": "user", "content": build_prompt(question, contexts)},
        ],
        "temperature": 0.2,
    }


def build_claude_payload(
    question: str, contexts: list[RetrievedContext], model: str
) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": 700,
        "temperature": 0.2,
        "system": (
            "Answer from the provided context. If context is insufficient, "
            "say what is missing."
        ),
        "messages": [{"role": "user", "content": build_prompt(question, contexts)}],
    }


def build_gemini_payload(
    question: str, contexts: list[RetrievedContext], model: str
) -> dict[str, Any]:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Answer from the provided context. If context is insufficient, "
                            f"say what is missing.\n\n{build_prompt(question, contexts)}"
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 700,
        },
    }


def parse_openai_response(data: dict[str, Any]) -> str:
    return str(data["choices"][0]["message"]["content"])


def parse_claude_response(data: dict[str, Any]) -> str:
    parts = [
        block["text"]
        for block in data.get("content", [])
        if block.get("type") == "text" and block.get("text")
    ]
    return "\n".join(parts).strip()


def parse_gemini_response(data: dict[str, Any]) -> str:
    parts = []
    for candidate in data.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()
