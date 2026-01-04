"""Web search functionality using Tavily API."""

from pydantic import BaseModel
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential


class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    score: float


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def web_search(query: str, api_key: str, max_results: int = 3) -> list[SearchResult]:
    """Search the web using Tavily API with retry logic."""
    client = TavilyClient(api_key)
    response = client.search(query=query, max_results=max_results)
    results = response.get("results", [])

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
