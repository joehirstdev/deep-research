from pydantic import BaseModel
from tavily import TavilyClient


class TavilyResult(BaseModel):
    url: str
    title: str
    content: str
    score: float


def tavily_web_search(query: str, tavily_api_key: str, k: int = 3):
    client = TavilyClient(tavily_api_key)
    response = client.search(query=query)
    top_k = [
        TavilyResult(
            url=item["url"],
            title=item["title"],
            content=item["content"],
            score=item["score"],
        )
        for item in response["results"][:k]
    ]
    return top_k
