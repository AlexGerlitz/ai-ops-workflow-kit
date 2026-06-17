import re


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 120) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        window = normalized[start:end]
        if end < len(normalized):
            split_at = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
            if split_at > max_chars * 0.45:
                end = start + split_at + 1
                window = normalized[start:end]
        chunks.append(window.strip())
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks

