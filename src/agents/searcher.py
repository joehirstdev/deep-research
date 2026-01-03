"""Searcher Agent: Researches individual queries using web search + LLM synthesis."""

from openai import OpenAI

from src.agents.search import web_search, SearchResult
from src.utils import retry_with_backoff


class SearcherAgent:
    """Agent that researches a single query via web search and LLM synthesis."""

    def __init__(
        self, llm_client: OpenAI, search_api_key: str, model: str = "gemini-2.5-flash"
    ):
        self.client = llm_client
        self.search_api_key = search_api_key
        self.model = model

    @retry_with_backoff(max_retries=2)
    def research(self, query: str) -> tuple[str, str, list[str]]:
        """Research a query and return answer, context, and source links."""
        try:
            # Step 1: Web search
            search_results = web_search(query, self.search_api_key, max_results=3)

            if not search_results:
                return (
                    "No search results found for this query.",
                    "No context available",
                    [],
                )

            # Step 2: Format context
            context_content = self._format_context(search_results)
            links = [result.url for result in search_results]

            # Step 3: Synthesize with LLM
            answer = self._synthesize_answer(query, context_content)

            if not answer:
                raise ValueError("Empty response from LLM")

            return answer, context_content, links

        except Exception as e:
            raise RuntimeError(f"Research failed for query '{query}': {e}")

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
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"query: {query}, context: {context}"},
            ],
        )
        return response.choices[0].message.content or ""
