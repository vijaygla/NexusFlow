"""
NexusFlow Application Configuration
Loads environment variables securely using Pydantic Settings.
"""

from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production-grade settings management for NexusFlow backend."""

    # Project Information
    PROJECT_NAME: str = "NexusFlow Multi-Agent System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Generative Engine LLM Provider Configuration
    OPENAI_API_KEY: str = Field(..., description="Capgemini Generative Engine / OpenAI API Key")
    OPENAI_BASE_URL: str = Field(
        default="https://openai.generative.engine.capgemini.com/v1",
        description="Base URL for OpenAI-compatible completions",
    )

    # Multi-Agent Model Assignments
    CODER_MODEL: str = Field(
        default="qwen.qwen3-coder-30b-a3b-v1:0",
        description="High-performance code generation and synthesis model",
    )
    REVIEWER_MODEL: str = Field(
        default="anthropic.claude-sonnet-5",
        description="Strict semantic and architectural code review model",
    )
    DEFAULT_TEMPERATURE: float = 0.2
    MAX_ITERATIONS: int = 3

    # Security & CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:4200", "http://127.0.0.1:4200"]

    # MS SQL Server Persistence Settings
    DB_ENABLED: bool = True
    DB_SERVER: str = "LIN-5CD6268KRS"
    DB_DATABASE: str = "NexusFlowDb"
    DB_USER: str = "sa"
    DB_PASSWORD: str = "Capgemini@12345"
    DB_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_TRUST_SERVER_CERTIFICATE: str = "yes"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def sql_connection_string(self) -> str:
        """Constructs an ODBC connection string for MS SQL Server."""
        return (
            f"Driver={{{self.DB_DRIVER}}};"
            f"Server={self.DB_SERVER};"
            f"Database={self.DB_DATABASE};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
            f"TrustServerCertificate={self.DB_TRUST_SERVER_CERTIFICATE};"
            f"Connection Timeout=5;"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Returns singleton instance of application settings."""
    return Settings()
