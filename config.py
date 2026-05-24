import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    """
    Application settings for the Gemini-native Intelligence Harness.
    """

    # --- Gemini API Settings ---
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API Key (from AI Studio)"
    )
    gemini_default_model: str = Field(
        default="gemini-1.5-flash",
        description="Default Gemini model to use"
    )
    gemini_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Timeout for Gemini requests"
    )

    # --- Storage & DB Settings ---
    database_url: str = Field(
        default="sqlite:///./data/gemini_harness.db",
        description="SQLite database URL for harness memory"
    )

    # --- Operations Settings ---
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    dry_run: bool = Field(
        default=True,
        description="If True, performs dry-run content updates"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = v.upper()
        if normalized not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}, got '{v}'")
        return normalized

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
