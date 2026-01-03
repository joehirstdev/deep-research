"""Planner Agent: Decomposes complex queries into focused sub-questions."""

import json
from pydantic import BaseModel, field_validator
from openai import OpenAI

from src.utils import retry_with_backoff


class ResearchPlan(BaseModel):
    """Research plan with decomposed sub-questions."""

    original_query: str
    sub_questions: list[str]
    reasoning: str


class PlannerAgent:
    """Agent that breaks down complex queries into researchable sub-questions."""

    def __init__(self, llm_client: OpenAI, model: str = "gemini-2.5-flash"):
        self.client = llm_client
        self.model = model

    @retry_with_backoff(max_retries=3)
    def plan(self, query: str) -> ResearchPlan:
        """Decompose a complex query into focused sub-questions."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if len(query) > 1000:
            raise ValueError("Query too long (max 1000 characters)")

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

        user_prompt = (
            f"Original query: {query}\n\nDecompose this into focused sub-questions."
        )

        try:
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
                raise ValueError("Empty response from LLM")

            parsed = json.loads(content)

            if "sub_questions" not in parsed:
                raise ValueError("LLM response missing 'sub_questions' field")

            return ResearchPlan(
                original_query=query,
                sub_questions=parsed["sub_questions"],
                reasoning=parsed.get("reasoning", "No reasoning provided"),
            )

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate research plan: {e}")
