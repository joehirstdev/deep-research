"""Web search functionality using Tavily API."""

from pydantic import BaseModel
from tavily import TavilyClient

from src.utils import retry_with_backoff


class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    score: float


@retry_with_backoff(max_retries=3)
def web_search(query: str, api_key: str, max_results: int = 3) -> list[SearchResult]:
    """Search the web using Tavily API with retry logic."""
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if not api_key:
        raise ValueError("API key is required")

    try:
        client = TavilyClient(api_key)
        response = client.search(query=query, max_results=max_results)

        if not response or "results" not in response:
            raise ValueError("Invalid response from Tavily API")

        results = response.get("results", [])

        if not results:
            return []

        return [
            SearchResult(
                url=item.get("url", ""),
                title=item.get("title", "Untitled"),
                content=item.get("content", ""),
                score=item.get("score", 0.0),
            )
            for item in results[:max_results]
            if item.get("url")
        ]

    except Exception as e:
        raise RuntimeError(f"Web search failed: {e}")
