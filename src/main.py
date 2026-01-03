from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
import json
import asyncio

from src.settings import Settings
from src.tavily import tavily_web_search
from src.agents.planner import PlannerAgent


settings = Settings()  # pyright: ignore [reportCallIssue]


app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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


@app.post("/research/stream")
async def research_stream(body: dict):
    """Streaming multi-agent research endpoint with real-time progress updates."""
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    async def event_generator():
        """Generate SSE events for research progress."""

        def send_event(event_type: str, data: dict):
            """Format and return SSE event."""
            return f"data: {json.dumps({'type': event_type, **data})}\n\n"

        try:
            # Step 1: Planning
            yield send_event("progress", {"message": "Planning research strategy..."})
            await asyncio.sleep(0)  # Force flush

            plan = await asyncio.to_thread(planner.plan, query)
            yield send_event(
                "plan",
                {
                    "sub_questions": plan.sub_questions,
                    "reasoning": plan.reasoning,
                    "total": len(plan.sub_questions),
                },
            )
            await asyncio.sleep(0)  # Force flush

            # Step 2: Research each sub-question
            sub_results = []
            all_links = []

            for idx, sub_q in enumerate(plan.sub_questions, 1):
                yield send_event(
                    "progress",
                    {
                        "message": f"Researching {idx}/{len(plan.sub_questions)}: {sub_q}",
                        "current": idx,
                        "total": len(plan.sub_questions),
                    },
                )
                await asyncio.sleep(0)  # Force flush

                result, context, links = await asyncio.to_thread(main, sub_q)
                sub_result = {
                    "index": idx,
                    "question": sub_q,
                    "answer": result,
                    "sources": links,
                }
                sub_results.append(sub_result)
                all_links.extend(links)

                yield send_event("sub_result", sub_result)
                await asyncio.sleep(0)  # Force flush

            # Step 3: Synthesize
            yield send_event("progress", {"message": "Synthesizing final answer..."})
            await asyncio.sleep(0)  # Force flush

            synthesis_context = "\n\n".join(
                [f"Q: {r['question']}\nA: {r['answer']}" for r in sub_results]
            )

            final_answer = await asyncio.to_thread(
                lambda: client.chat.completions.create(
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

            yield send_event("final", {"answer": final_answer})
            await asyncio.sleep(0)  # Force flush

            # Complete
            yield send_event(
                "complete",
                {
                    "all_sources": list(set(all_links)),
                    "total_sub_questions": len(plan.sub_questions),
                },
            )

        except Exception as e:
            yield send_event("error", {"message": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
