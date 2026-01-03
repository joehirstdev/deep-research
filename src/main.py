from typing import Any
from fastapi import FastAPI, HTTPException, status
from openai import OpenAI
from pydantic import BaseModel

from src.settings import Settings
from src.tavily import tavily_web_search


settings = Settings()  # pyright: ignore [reportCallIssue]


app = FastAPI()

client = OpenAI(
    api_key=settings.gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


def main(query: str):
    context = tavily_web_search(query, settings.tavily_api_key)
    context_content = "\n".join(
        [
            f"""# {item.title.strip()}
URL: {item.url.strip()}
Content: {item.content.strip()}
---
"""
            for item in context
        ]
    ).strip()
    links = [result.url for result in context]

    llm_response = (
        client.chat.completions.create(
            model="gemini-2.5-flash",
            reasoning_effort="low",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": f"query: {query}, context: {context_content}",
                },
            ],
        )
        .choices[0]
        .message.content
    )

    return llm_response, context_content, links


class Response(BaseModel):
    text: str
    context_content: str
    links: list[str]


@app.get("/test/{query}")
def test(query: str) -> Response:
    result, context_content, links = main(query)
    if not result:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(text=result, context_content=context_content, links=links)
