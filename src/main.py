from fastapi import FastAPI, HTTPException, status
from openai import OpenAI
from pydantic import BaseModel

from src.settings import Settings
from src.tavily import tavily_web_search
from src.agents.planner import PlannerAgent


settings = Settings()  # pyright: ignore [reportCallIssue]


app = FastAPI()

client = OpenAI(
    api_key=settings.gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

planner = PlannerAgent(llm_client=client)


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
            model=settings.gemini_model,
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


@app.post("/research")
def research(body: dict) -> dict:
    """Multi-agent research endpoint using planner."""
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    # Step 1: Plan - decompose query into sub-questions
    plan = planner.plan(query)

    # Step 2: Research each sub-question
    sub_results = []
    all_links = []
    for sub_q in plan.sub_questions:
        result, context, links = main(sub_q)
        sub_results.append({"question": sub_q, "answer": result, "sources": links})
        all_links.extend(links)

    # Step 3: Synthesize findings
    synthesis_context = "\n\n".join(
        [f"Q: {r['question']}\nA: {r['answer']}" for r in sub_results]
    )

    final_answer = (
        client.chat.completions.create(
            model=settings.gemini_model,
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
        .choices[0]
        .message.content
    )

    return {
        "query": query,
        "plan": plan.model_dump(),
        "sub_results": sub_results,
        "final_answer": final_answer,
        "all_sources": list(set(all_links)),
    }
