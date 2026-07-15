"""Application settings loaded from environment / .env via pydantic-settings."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration in one place. Values come from the
    environment or a `.env` file; every field can be overridden per-run."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),  # allow the `model_name` field
    )

    # API keys (validated at startup by `validate_keys`)
    google_api_key: str = Field(default="", description="Gemini API key")
    tavily_api_key: str = Field(default="", description="Tavily search API key")

    # Model / agent behaviour
    model_name: str = Field(default="gemini-3-pro-preview", description="Gemini model id")
    max_iterations: int = Field(default=3, ge=1, description="Max plan→research→critique loops")
    max_search_results: int = Field(default=3, ge=1, description="Tavily results per sub-question")
    scrape_char_limit: int = Field(default=2000, ge=100, description="Max chars kept from a scraped page")

    def validate_keys(self) -> None:
        """Fail fast with a clear message if required API keys are missing."""
        missing = []
        if not self.google_api_key:
            missing.append("GOOGLE_API_KEY")
        if not self.tavily_api_key:
            missing.append("TAVILY_API_KEY")
        if missing:
            raise RuntimeError(
                f"Missing required API key(s): {', '.join(missing)}. "
                "Set them in your environment or in a .env file "
                "(see .env.example)."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
