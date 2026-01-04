"""FastAPI application for multi-agent research with streaming responses."""

import asyncio
import json
import secrets
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field

from src.agents.planner import PlannerAgent
from src.agents.researcher import ResearcherAgent
from src.agents.synthesizer import SynthesizerAgent
from src.settings import Settings

settings = Settings()  # pyright: ignore [reportCallIssue]

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify Basic Auth credentials."""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), settings.basic_auth_username.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"), settings.basic_auth_password.encode("utf8")
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


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
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

# Initialize agents
planner = PlannerAgent(llm_client=client, model=settings.llm_model)
researcher = ResearcherAgent(llm_client=client, search_api_key=settings.tavily_api_key, model=settings.llm_model)
synthesizer = SynthesizerAgent(llm_client=client, model=settings.llm_model)


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)


@app.post("/login")
async def login(username: Annotated[str, Depends(verify_credentials)]) -> dict[str, str]:
    """Verify credentials and return success."""
    return {"message": "Login successful", "username": username}


@app.post("/research/stream")
async def research_stream(
    request: ResearchRequest, username: Annotated[str, Depends(verify_credentials)]
) -> StreamingResponse:
    """Streaming multi-agent research endpoint with real-time progress updates."""
    query = request.query

    async def event_generator() -> AsyncGenerator[str]:
        """Generate SSE events for research progress."""

        def send_event(event_type: str, data: dict) -> str:
            """Format and return SSE event."""
            return f"data: {json.dumps({'type': event_type, **data})}\n\n"

        try:
            # Step 1: Planning
            yield send_event("progress", {"message": "Planning research strategy..."})
            await asyncio.sleep(0)

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
            await asyncio.sleep(0)

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
                    links = await asyncio.to_thread(researcher.get_sources, sub_q)
                    yield send_event(
                        "sources",
                        {
                            "index": idx,
                            "sources": links,
                        },
                    )
                    await asyncio.sleep(0)

                    # Step 3: Do full research (synthesis) and show answer
                    result, _ = await asyncio.to_thread(researcher.research, sub_q)
                    yield send_event(
                        "answer",
                        {
                            "index": idx,
                            "answer": result,
                        },
                    )
                    await asyncio.sleep(0)

                    sub_results.append({"question": sub_q, "answer": result, "sources": links})
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
            await asyncio.sleep(0)

            try:
                final_answer = await asyncio.to_thread(synthesizer.synthesize, query, sub_results)
                yield send_event("final", {"answer": final_answer})
                await asyncio.sleep(0)
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
