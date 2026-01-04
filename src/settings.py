"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_api_key: str = Field(..., alias="LLM_API_KEY")
    llm_model: str = Field(..., alias="LLM_MODEL")
    llm_base_url: str = Field(..., alias="LLM_BASE_URL")
    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")
