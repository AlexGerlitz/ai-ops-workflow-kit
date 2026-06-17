import httpx

from app.schemas import RetrievedContext


class LLMClient:
    def __init__(self, *, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def answer(self, question: str, contexts: list[RetrievedContext]) -> str:
        if not contexts:
            return "No relevant context was found."
        if not self.api_key:
            return self._extractive_answer(question, contexts)
        return await self._openai_answer(question, contexts)

    def _extractive_answer(self, question: str, contexts: list[RetrievedContext]) -> str:
        joined = " ".join(context.text for context in contexts[:2])
        return f"Draft answer for: {question}\n\nContext: {joined[:1200]}"

    async def _openai_answer(self, question: str, contexts: list[RetrievedContext]) -> str:
        context_text = "\n\n".join(
            f"Source: {context.source}\n{context.text}" for context in contexts
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Answer from the provided context. If context is insufficient, say what is missing.",
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nContext:\n{context_text}",
                },
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

