"""Load and validate environment-backed settings for Contribution Compass."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

load_dotenv()

ModelProvider = Literal["gemini", "openai-oauth"]


class Settings(BaseModel):
    """Validated runtime configuration. Secrets are never printed."""

    github_token: str | None = None
    github_api_url: str = "https://api.github.com"
    model_provider: ModelProvider = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_base_url: str = "http://127.0.0.1:10531/v1"
    openai_model: str = "gpt-5.6-terra"
    openai_api_key: str = "sk-local"
    search_result_limit: int = Field(default=20, ge=1, le=50)

    @model_validator(mode="after")
    def _require_provider_credentials(self) -> Settings:
        if self.model_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "MODEL_PROVIDER=gemini requires GEMINI_API_KEY "
                "(or GOOGLE_API_KEY)."
            )
        if self.model_provider == "openai-oauth" and not self.openai_base_url:
            raise ValueError(
                "MODEL_PROVIDER=openai-oauth requires OPENAI_BASE_URL "
                "(default http://127.0.0.1:10531/v1 from bunx openai-oauth)."
            )
        return self


def _resolve_provider(raw: str | None, *, has_gemini_key: bool) -> ModelProvider:
    value = (raw or "").strip().lower().replace("_", "-")
    if value in {"openai-oauth", "openai", "oauth", "chatgpt"}:
        return "openai-oauth"
    if value in {"gemini", "antigravity", "google"}:
        return "gemini"
    if value == "":
        # Prefer Gemini when a key exists; otherwise use the local oauth proxy.
        return "gemini" if has_gemini_key else "openai-oauth"
    raise ValueError(
        f"Unsupported MODEL_PROVIDER={raw!r}. Use 'gemini' or 'openai-oauth'."
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read environment variables once and return validated settings."""
    # @lat: [[lat.md/lat#Configuration]]
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    provider = _resolve_provider(
        os.getenv("MODEL_PROVIDER"),
        has_gemini_key=bool(gemini_key),
    )
    return Settings(
        github_token=os.getenv("GITHUB_TOKEN") or None,
        github_api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
        model_provider=provider,
        gemini_api_key=gemini_key or None,
        gemini_model=os.getenv("GEMINI_MODEL") or None,
        openai_base_url=(
            os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:10531/v1")
            .rstrip("/")
        ),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-terra"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "sk-local"),
        search_result_limit=int(os.getenv("SEARCH_RESULT_LIMIT", "20")),
    )
