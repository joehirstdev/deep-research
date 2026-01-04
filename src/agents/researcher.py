"""Researcher Agent: Researches individual queries using web search + LLM synthesis."""

import structlog
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.agents.search import SearchResult, web_search

logger = structlog.get_logger()


class ResearcherAgent:
    def __init__(self, llm_client: OpenAI, search_api_key: str, model: str) -> None:
        self.client = llm_client
        self.search_api_key = search_api_key
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def research(self, query: str) -> tuple[str, list[str]]:
        """Research a query and return answer and source links."""
        search_results = web_search(query, self.search_api_key, max_results=3)

        if not search_results:
            logger.warning("no_search_results")
            return "No search results found for this query.", []

        context_content = self._format_context(search_results)
        links = [result.url for result in search_results]
        answer = self._synthesize_answer(query, context_content)

        logger.debug("research_completed", sources_count=len(links))
        return answer, links

    def get_sources(self, query: str) -> list[str]:
        """Get sources for a query without synthesis (faster)."""
        search_results = web_search(query, self.search_api_key, max_results=3)
        return [result.url for result in search_results]

    def _format_context(self, results: list[SearchResult]) -> str:
        """Format search results into context string."""
        return "\n".join(
            [
                f"""# {result.title.strip()}
URL: {result.url.strip()}
Content: {result.content.strip()}
---
"""
                for result in results
            ]
        ).strip()

    def _synthesize_answer(self, query: str, context: str) -> str:
        """Synthesize answer from context using LLM."""
        response = self.client.chat.completions.create(
            model=self.model,
            reasoning_effort="low",
            messages=[
                {
                    "role": "system",
                    "content": "You are a research assistant. Answer the question accurately using the provided web search context. Be factual and concise.",
                },
                {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
            ],
        )
        return response.choices[0].message.content or ""
