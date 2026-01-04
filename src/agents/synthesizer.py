"""Synthesizer Agent: Combines research findings into comprehensive answers."""

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential


class SynthesizerAgent:
    def __init__(self, llm_client: OpenAI, model: str) -> None:
        self.client = llm_client
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def synthesize(self, query: str, sub_results: list[dict]) -> str:
        """Synthesize sub-question answers into a comprehensive final answer."""
        synthesis_context = "\n\n".join([f"Q: {r['question']}\nA: {r['answer']}" for r in sub_results])

        response = self.client.chat.completions.create(
            model=self.model,
            reasoning_effort="medium",
            messages=[
                {
                    "role": "system",
                    "content": "You are a research synthesizer. Combine findings into a comprehensive, well-structured answer.",
                },
                {
                    "role": "user",
                    "content": f"Original query: {query}\n\nFindings:\n{synthesis_context}\n\nProvide a comprehensive answer with citations.",
                },
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response")
        return content
