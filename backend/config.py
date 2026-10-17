"""Configuration settings for Gig-Aid."""

from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Configuration
    PROJECT_NAME: str = "Gig-Aid"
    PROJECT_DESCRIPTION: str = (
        "Pan-India, multilingual GenAI grievance assistant for gig and informal workers."
    )
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", alias="ENVIRONMENT")

    # Server settings (dynamically respects Cloud Run's $PORT)
    HOST: str = Field(default="0.0.0.0", alias="HOST")
    PORT: int = Field(default=8080, alias="PORT")

    # GenAI Provider Settings (configurable model, API key from managed secrets)
    GEMINI_API_KEY: str = Field(default="", alias="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    REQUEST_TIMEOUT_SECONDS: float = Field(default=30.0, alias="REQUEST_TIMEOUT_SECONDS")

    # Security & Guardrails
    MAX_INPUT_LENGTH: int = Field(default=4000, alias="MAX_INPUT_LENGTH")
    MAX_OUTPUT_TOKENS: int = Field(default=2048, alias="MAX_OUTPUT_TOKENS")
    CORS_ORIGINS: List[str] = ["*"]


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
