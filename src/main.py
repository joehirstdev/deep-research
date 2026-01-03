from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator
import json
import asyncio

from src.settings import Settings
from src.agents.planner import PlannerAgent
from src.agents.searcher import SearcherAgent


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

# Initialize agents
planner = PlannerAgent(llm_client=client)
searcher = SearcherAgent(
    llm_client=client, search_api_key=settings.tavily_api_key, model=settings.gemini_model
)




class Response(BaseModel):
    text: str
    context_content: str
    links: list[str]


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and clean query."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty or whitespace")
        return v


@app.get("/test/{query}")
def test(query: str) -> Response:
    """Simple search endpoint without query decomposition."""
    try:
        # Validate query length
        if len(query) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Query too long"
            )

        result, context_content, links = searcher.research(query)
        return Response(text=result, context_content=context_content, links=links)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {e}",
        )


@app.post("/research")
def research(request: ResearchRequest) -> dict:
    """Multi-agent research endpoint using planner."""
    try:
        # Step 1: Plan - decompose query into sub-questions
        plan = planner.plan(request.query)

        # Step 2: Research each sub-question
        sub_results = []
        all_links = []
        for sub_q in plan.sub_questions:
            try:
                result, context, links = searcher.research(sub_q)
                sub_results.append(
                    {"question": sub_q, "answer": result, "sources": links}
                )
                all_links.extend(links)
            except Exception as e:
                # Log error but continue with other questions
                sub_results.append(
                    {
                        "question": sub_q,
                        "answer": f"Error researching this question: {e}",
                        "sources": [],
                    }
                )

        if not sub_results:
            raise RuntimeError("Failed to research any sub-questions")

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
                        "content": f"Original query: {request.query}\n\nFindings:\n{synthesis_context}\n\nProvide a comprehensive answer with citations.",
                    },
                ],
            )
            .choices[0]
            .message.content
        )

        if not final_answer:
            raise ValueError("Empty final answer from synthesizer")

        return {
            "query": request.query,
            "plan": plan.model_dump(),
            "sub_results": sub_results,
            "final_answer": final_answer,
            "all_sources": list(set(all_links)),
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {e}",
        )


@app.post("/research/stream")
async def research_stream(request: ResearchRequest):
    """Streaming multi-agent research endpoint with real-time progress updates."""
    query = request.query

    async def event_generator():
        """Generate SSE events for research progress."""

        def send_event(event_type: str, data: dict):
            """Format and return SSE event."""
            return f"data: {json.dumps({'type': event_type, **data})}\n\n"

        try:
            # Step 1: Planning
            yield send_event("progress", {"message": "Planning research strategy..."})
            await asyncio.sleep(0)  # Force flush

            try:
                plan = await asyncio.to_thread(planner.plan, query)
            except Exception as e:
                yield send_event("error", {"message": f"Planning failed: {e}"})
                return
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
                # Step 1: Show question
                yield send_event(
                    "question",
                    {
                        "index": idx,
                        "question": sub_q,
                        "total": len(plan.sub_questions),
                    },
                )
                await asyncio.sleep(0)

                try:
                    # Step 2: Get and show sources
                    links = await asyncio.to_thread(searcher.get_sources, sub_q)
                    yield send_event(
                        "sources",
                        {
                            "index": idx,
                            "sources": links,
                        },
                    )
                    await asyncio.sleep(0)

                    # Step 3: Do full research (synthesis) and show answer
                    result, context, _ = await asyncio.to_thread(
                        searcher.research, sub_q
                    )
                    yield send_event(
                        "answer",
                        {
                            "index": idx,
                            "answer": result,
                        },
                    )
                    await asyncio.sleep(0)

                    sub_results.append(
                        {"question": sub_q, "answer": result, "sources": links}
                    )
                    all_links.extend(links)

                except Exception as e:
                    # Log error but continue with other questions
                    error_result = {
                        "index": idx,
                        "question": sub_q,
                        "answer": f"Error: {e}",
                        "sources": [],
                    }
                    sub_results.append(error_result)
                    yield send_event(
                        "answer",
                        {
                            "index": idx,
                            "answer": f"Error: {e}",
                        },
                    )
                    await asyncio.sleep(0)

            # Step 3: Show all accumulated sources before synthesis
            if not sub_results:
                yield send_event("error", {"message": "No results to synthesize"})
                return

            yield send_event(
                "all_sources",
                {
                    "sources": list(set(all_links)),
                    "total": len(set(all_links)),
                },
            )
            await asyncio.sleep(0)

            # Step 4: Synthesize
            yield send_event("progress", {"message": "Synthesizing final answer..."})
            await asyncio.sleep(0)  # Force flush

            synthesis_context = "\n\n".join(
                [f"Q: {r['question']}\nA: {r['answer']}" for r in sub_results]
            )

            try:
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

                if not final_answer:
                    raise ValueError("Empty response from synthesizer")

                yield send_event("final", {"answer": final_answer})
                await asyncio.sleep(0)  # Force flush
            except Exception as e:
                yield send_event("error", {"message": f"Synthesis failed: {e}"})
                return

            # Complete
            yield send_event(
                "complete",
                {"total_sub_questions": len(plan.sub_questions)},
            )

        except Exception as e:
            yield send_event("error", {"message": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
