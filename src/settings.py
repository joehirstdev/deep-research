from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model: str = Field(..., alias="GEMINI_MODEL")
    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")
