from __future__ import annotations

import re
from typing import Any

from app.schemas import (
    CallAudioWebhookIn,
    TranscriptionOut,
    TranscriptionProviderRuntimeOut,
    TranscriptionRuntimeOut,
    TranscriptionSegmentOut,
    TranscriptionStatus,
)
from app.settings import Settings

SUPPORTED_TRANSCRIPTION_PROVIDERS = ("local_stub", "openai_whisper", "deepgram")


def transcription_runtime(config: Settings) -> TranscriptionRuntimeOut:
    selected = select_provider(config.transcription_provider)
    providers = [
        provider_runtime(
            provider,
            config=config,
            selected=provider == selected,
        )
        for provider in SUPPORTED_TRANSCRIPTION_PROVIDERS
    ]
    return TranscriptionRuntimeOut(
        requested_provider=config.transcription_provider,
        selected_provider=selected,
        dry_run=config.transcription_dry_run,
        supported_providers=list(SUPPORTED_TRANSCRIPTION_PROVIDERS),
        providers=providers,
    )


def provider_runtime(
    provider: str,
    *,
    config: Settings,
    selected: bool,
) -> TranscriptionProviderRuntimeOut:
    required_env = required_env_for_provider(provider)
    configured = provider == "local_stub" or all(getattr(config, env_attr(env)) for env in required_env)
    notes = {
        "local_stub": (
            "Deterministic local transcription fixture for public demos and tests; "
            "no external audio service is called."
        ),
        "openai_whisper": (
            "Adapter contract for OpenAI Whisper transcription. Public mode stays dry-run "
            "until audio storage and OPENAI_API_KEY are configured."
        ),
        "deepgram": (
            "Adapter contract for Deepgram transcription and diarization. Public mode stays dry-run "
            "until audio storage and DEEPGRAM_API_KEY are configured."
        ),
    }[provider]
    return TranscriptionProviderRuntimeOut(
        provider=provider,
        configured=configured,
        selected=selected,
        dry_run=config.transcription_dry_run,
        required_env=required_env,
        notes=notes,
    )


def transcribe_call_audio(payload: CallAudioWebhookIn, config: Settings) -> TranscriptionOut:
    provider = select_provider(payload.provider or config.transcription_provider)
    request_contract = build_request_contract(provider, payload, config)
    transcript = normalize_transcript(payload.transcript_hint or "")

    if provider == "local_stub":
        if not transcript:
            raise ValueError("local_stub transcription requires transcript_hint")
        return TranscriptionOut(
            provider=provider,
            status=TranscriptionStatus.dry_run,
            audio_uri=payload.audio_uri,
            audio_mime_type=payload.audio_mime_type,
            language=payload.language,
            duration_seconds=payload.duration_seconds,
            transcript=transcript,
            segments=build_segments(transcript, payload.duration_seconds),
            confidence=0.99,
            detail="Dry-run local transcription fixture generated a normalized transcript.",
            request_contract=request_contract,
        )

    if config.transcription_dry_run:
        if not transcript:
            raise ValueError(f"{provider} dry-run requires transcript_hint")
        return TranscriptionOut(
            provider=provider,
            status=TranscriptionStatus.dry_run,
            audio_uri=payload.audio_uri,
            audio_mime_type=payload.audio_mime_type,
            language=payload.language,
            duration_seconds=payload.duration_seconds,
            transcript=transcript,
            segments=build_segments(transcript, payload.duration_seconds),
            confidence=None,
            detail=f"{provider} dry-run built the transcription request contract without external calls.",
            request_contract=request_contract,
        )

    missing = [env for env in required_env_for_provider(provider) if not getattr(config, env_attr(env))]
    if missing:
        return TranscriptionOut(
            provider=provider,
            status=TranscriptionStatus.not_configured,
            audio_uri=payload.audio_uri,
            audio_mime_type=payload.audio_mime_type,
            language=payload.language,
            duration_seconds=payload.duration_seconds,
            transcript="",
            segments=[],
            confidence=None,
            detail=f"{provider} is missing required environment: {', '.join(missing)}.",
            request_contract=request_contract,
        )

    raise ValueError(f"{provider} live transcription is not enabled in this public skeleton")


def select_provider(provider: str) -> str:
    normalized = provider.strip().lower().replace("-", "_")
    aliases = {
        "whisper": "openai_whisper",
        "openai": "openai_whisper",
        "openai_whisper": "openai_whisper",
        "deepgram": "deepgram",
        "local": "local_stub",
        "local_stub": "local_stub",
    }
    selected = aliases.get(normalized)
    if selected not in SUPPORTED_TRANSCRIPTION_PROVIDERS:
        raise ValueError(f"unsupported transcription provider: {provider}")
    return selected


def required_env_for_provider(provider: str) -> list[str]:
    if provider == "openai_whisper":
        return ["OPENAI_API_KEY"]
    if provider == "deepgram":
        return ["DEEPGRAM_API_KEY"]
    return []


def env_attr(env: str) -> str:
    return {
        "OPENAI_API_KEY": "openai_api_key",
        "DEEPGRAM_API_KEY": "deepgram_api_key",
    }[env]


def build_request_contract(
    provider: str,
    payload: CallAudioWebhookIn,
    config: Settings,
) -> dict[str, Any]:
    common = {
        "audio_uri": payload.audio_uri,
        "audio_mime_type": payload.audio_mime_type,
        "language": payload.language,
        "duration_seconds": payload.duration_seconds,
        "secret_fields": required_env_for_provider(provider),
    }
    if provider == "openai_whisper":
        return {
            "method": "POST",
            "url": "https://api.openai.com/v1/audio/transcriptions",
            "model": config.whisper_model,
            "body": {
                "file": "binary audio from audio_uri",
                "model": config.whisper_model,
                "language": payload.language,
                "response_format": "verbose_json",
            },
            **common,
        }
    if provider == "deepgram":
        return {
            "method": "POST",
            "url": "https://api.deepgram.com/v1/listen",
            "query": {
                "model": config.deepgram_model,
                "diarize": "true",
                "smart_format": "true",
                "language": payload.language,
            },
            "body": {"url": payload.audio_uri},
            **common,
        }
    return {
        "method": "fixture",
        "url": "local://transcription-fixture",
        "body": {"transcript_hint": "normalized and segmented locally"},
        **common,
    }


def normalize_transcript(transcript: str) -> str:
    lines = [line.strip() for line in transcript.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(" ".join(line.split()) for line in lines)


def build_segments(
    transcript: str,
    duration_seconds: float | None,
) -> list[TranscriptionSegmentOut]:
    speaker_lines = parse_speaker_lines(transcript)
    if not speaker_lines:
        speaker_lines = [
            (f"speaker_{index % 2 + 1}", text)
            for index, text in enumerate(split_sentences(transcript))
        ]
    total = duration_seconds or max(len(transcript) / 14, len(speaker_lines) * 3.0)
    slice_seconds = total / max(len(speaker_lines), 1)
    segments = []
    for index, (speaker, text) in enumerate(speaker_lines):
        start = round(index * slice_seconds, 2)
        end = round((index + 1) * slice_seconds, 2)
        segments.append(
            TranscriptionSegmentOut(
                speaker=speaker,
                start_seconds=start,
                end_seconds=end,
                text=text,
            )
        )
    return segments


def parse_speaker_lines(transcript: str) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for line in transcript.splitlines():
        match = re.match(r"^([A-Za-zА-Яа-я0-9 _-]{2,32}):\s+(.+)$", line.strip())
        if not match:
            continue
        speaker = match.group(1).strip().lower().replace(" ", "_")
        text = match.group(2).strip()
        parsed.append((speaker, text))
    return parsed


def split_sentences(transcript: str) -> list[str]:
    normalized = " ".join(transcript.split())
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    return parts or [normalized]
