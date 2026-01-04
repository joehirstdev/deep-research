"""Planner Agent: Decomposes complex queries into focused sub-questions."""

import json

import structlog
from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class ResearchPlan(BaseModel):
    original_query: str
    sub_questions: list[str]
    reasoning: str


class PlannerAgent:
    def __init__(self, llm_client: OpenAI, model: str) -> None:
        self.client = llm_client
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def plan(self, query: str) -> ResearchPlan:
        """Decompose a complex query into focused sub-questions."""
        system_prompt = """You are a research planning expert. Your job is to break down complex queries into focused, answerable sub-questions.

Guidelines:
1. Generate 2-5 sub-questions that together thoroughly address the original query
2. Each sub-question should be specific and independently answerable
3. Order questions logically (foundational → specific)
4. Avoid redundant questions
5. Consider different angles: definitions, mechanisms, applications, comparisons, etc.

Return your response in this JSON format:
{
    "sub_questions": ["question 1", "question 2", ...],
    "reasoning": "Brief explanation of why these questions cover the query"
}"""

        user_prompt = f"Original query: {query}\n\nDecompose this into focused sub-questions."

        response = self.client.chat.completions.create(
            model=self.model,
            reasoning_effort="medium",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            logger.error("planner_empty_response")
            raise ValueError("Empty response")
        parsed = json.loads(content)

        plan = ResearchPlan(
            original_query=query,
            sub_questions=parsed["sub_questions"],
            reasoning=parsed.get("reasoning", "No reasoning provided"),
        )
        logger.debug("plan_created", sub_questions_count=len(plan.sub_questions))
        return plan
