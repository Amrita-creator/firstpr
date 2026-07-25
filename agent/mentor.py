"""Mentor agents: Antigravity (Gemini) or OpenAI SDK (openai-oauth proxy)."""

from __future__ import annotations

import asyncio
import json
from typing import TypeVar

import httpx
from google.antigravity import (
    Agent,
    BuiltinTools,
    CapabilitiesConfig,
    LocalAgentConfig,
)
from google.antigravity.hooks import policy
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, NotFoundError
from pydantic import BaseModel

from config import Settings, get_settings
from models import (
    ContributionBrief,
    MentorBriefDraft,
    RepositoryCandidate,
    SearchStrategy,
)

T = TypeVar("T", bound=BaseModel)


class MentorProviderError(RuntimeError):
    """Raised when the configured model provider cannot complete a request."""


def _mentor_capabilities() -> CapabilitiesConfig:
    """Only expose the finish tool so mentors cannot touch the filesystem."""
    # @lat: [[lat.md/lat#Read-only Safety]]
    return CapabilitiesConfig(
        enable_subagents=False,
        enabled_tools=[BuiltinTools.FINISH],
    )


def _normalize_openai_base_url(url: str) -> str:
    base = url.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return base


def _preflight_openai_oauth(settings: Settings) -> None:
    """Fail fast with a clear message if the local proxy is down or misrouted."""
    base = _normalize_openai_base_url(settings.openai_base_url)
    models_url = f"{base}/models"
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                models_url,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            )
    except httpx.RequestException as exc:
        raise MentorProviderError(
            "Cannot reach openai-oauth proxy at "
            f"{base}. Start it with: bunx openai-oauth --detach\n"
            f"Underlying error: {exc}"
        ) from exc

    if response.status_code == 404:
        raise MentorProviderError(
            f"openai-oauth returned 404 for {models_url}. "
            "Set OPENAI_BASE_URL=http://127.0.0.1:10531/v1 "
            "(include /v1, no trailing path)."
        )
    if response.status_code >= 400:
        raise MentorProviderError(
            f"openai-oauth /models failed ({response.status_code}): "
            f"{response.text[:300]}"
        )

    try:
        payload = response.json()
    except ValueError:
        return
    available = {
        item.get("id")
        for item in (payload.get("data") or [])
        if isinstance(item, dict)
    }
    if available and settings.openai_model not in available:
        sample = ", ".join(sorted(available)[:8])
        raise MentorProviderError(
            f"OPENAI_MODEL={settings.openai_model!r} is not exposed by the "
            f"proxy. Available: {sample}. "
            "Run `bunx openai-oauth status` and set OPENAI_MODEL."
        )


async def _run_structured_openai(
    *,
    system_instructions: str,
    prompt: str,
    response_schema: type[T],
    settings: Settings,
) -> T:
    """Chat Completions against bunx openai-oauth (OpenAI-compatible)."""
    # @lat: [[lat.md/lat#Model Providers]]
    _preflight_openai_oauth(settings)
    base = _normalize_openai_base_url(settings.openai_base_url)
    client = AsyncOpenAI(base_url=base, api_key=settings.openai_api_key)
    schema = response_schema.model_json_schema()
    # Remove unsupported keywords some proxies reject in strict mode.
    schema.pop("title", None)

    messages = [
        {"role": "system", "content": system_instructions},
        {
            "role": "user",
            "content": (
                f"{prompt}\n\n"
                f"Respond with JSON matching this schema:\n"
                f"{json.dumps(schema)}"
            ),
        },
    ]

    try:
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "schema": schema,
                    "strict": False,
                },
            },
        )
    except NotFoundError as exc:
        raise MentorProviderError(
            "openai-oauth returned 404 (route/model not found). "
            "Confirm the proxy is running (`bunx openai-oauth status`), "
            "OPENAI_BASE_URL ends with /v1, and OPENAI_MODEL is listed there. "
            f"Details: {exc}"
        ) from exc
    except APIConnectionError as exc:
        raise MentorProviderError(
            "Cannot connect to openai-oauth. "
            "Run: bunx openai-oauth login && bunx openai-oauth --detach"
        ) from exc
    except APIStatusError as exc:
        # Some ChatGPT-backed models reject json_schema; retry as plain JSON.
        if exc.status_code not in {400, 404, 422}:
            raise MentorProviderError(
                f"openai-oauth error ({exc.status_code}): {exc.message}"
            ) from exc
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            response_format={"type": "json_object"},
        )

    content = completion.choices[0].message.content if completion.choices else None
    if not content:
        raise MentorProviderError("openai-oauth returned an empty mentor response.")
    return response_schema.model_validate_json(content)


async def _run_structured_antigravity(
    *,
    system_instructions: str,
    prompt: str,
    response_schema: type[T],
    settings: Settings,
) -> T:
    """Antigravity local harness against Gemini."""
    config = LocalAgentConfig(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        system_instructions=system_instructions,
        response_schema=response_schema,
        capabilities=_mentor_capabilities(),
        policies=[policy.allow_all()],
        tools=[],
    )
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        data = await response.structured_output()
        if data is None:
            text = await response.text()
            raise MentorProviderError(
                "Mentor returned no structured output. "
                f"Raw response (truncated): {text[:500]!r}"
            )
        if isinstance(data, response_schema):
            return data
        return response_schema.model_validate(data)


async def _run_structured(
    *,
    system_instructions: str,
    prompt: str,
    response_schema: type[T],
    settings: Settings,
) -> T:
    if settings.model_provider == "openai-oauth":
        return await _run_structured_openai(
            system_instructions=system_instructions,
            prompt=prompt,
            response_schema=response_schema,
            settings=settings,
        )
    return await _run_structured_antigravity(
        system_instructions=system_instructions,
        prompt=prompt,
        response_schema=response_schema,
        settings=settings,
    )


async def analyze_profile_for_search_async(
    user_summary: dict,
    settings: Settings | None = None,
) -> SearchStrategy:
    """Ask the mentor to turn a GitHub summary into a SearchStrategy."""
    # @lat: [[lat.md/lat#Mentor Agents]]
    settings = settings or get_settings()
    prompt = f"""
Analyze this developer's GitHub activity summary and return a search strategy
for beginner/intermediate open-source projects they can contribute to.

Summary:
{json.dumps(user_summary, indent=2)}

Choose a realistic primary language, a short topic list, recommended issue
labels (include good-first-issue), and a star range that favors approachable
repos rather than huge projects.
""".strip()
    return await _run_structured(
        system_instructions=(
            "You are an open-source advisor. Infer only from the provided "
            "GitHub summary. Prefer approachable repos for first contributions."
        ),
        prompt=prompt,
        response_schema=SearchStrategy,
        settings=settings,
    )


async def generate_contribution_brief_async(
    username: str,
    top_repo: RepositoryCandidate,
    alternatives: list[RepositoryCandidate],
    settings: Settings | None = None,
) -> ContributionBrief:
    """Generate a ContributionBrief for the top ranked repository."""
    settings = settings or get_settings()
    alt_payload = [
        {
            "full_name": repo.full_name,
            "html_url": repo.html_url,
            "description": repo.description,
            "primary_language": repo.primary_language,
        }
        for repo in alternatives
    ]
    prompt = f"""
Learner GitHub username: {username}

Top recommended repository:
- full_name: {top_repo.full_name}
- url: {top_repo.html_url}
- description: {top_repo.description}
- language: {top_repo.primary_language}
- topics: {top_repo.topics}
- stars: {top_repo.stars}
- has_contributing_guide: {top_repo.has_contributing_guide}
- has_beginner_issues: {top_repo.has_beginner_issues}
- beginner_issue_url: {top_repo.beginner_issue_url}

Alternative repositories (optional context):
{json.dumps(alt_payload, indent=2)}

Return why_this_is_a_match (3-5 concrete reasons grounded in the data) and
suggested_first_steps (3 clear actionable steps; mention the beginner issue
URL when present).

Do not claim you opened issues, branches, or pull requests.
""".strip()
    draft = await _run_structured(
        system_instructions=(
            "You are a friendly open-source mentor. Explain only from provided "
            "repository evidence. Never invent GitHub write actions."
        ),
        prompt=prompt,
        response_schema=MentorBriefDraft,
        settings=settings,
    )
    return ContributionBrief(
        learner_username=username,
        top_recommendation=top_repo,
        alternative_options=alternatives,
        why_this_is_a_match=draft.why_this_is_a_match,
        suggested_first_steps=draft.suggested_first_steps,
    )


def analyze_profile_for_search(
    user_summary: dict,
    settings: Settings | None = None,
) -> SearchStrategy:
    """Sync wrapper around analyze_profile_for_search_async."""
    return asyncio.run(
        analyze_profile_for_search_async(user_summary, settings=settings)
    )


def generate_contribution_brief(
    username: str,
    top_repo: RepositoryCandidate,
    alternatives: list[RepositoryCandidate],
    settings: Settings | None = None,
) -> ContributionBrief:
    """Sync wrapper around generate_contribution_brief_async."""
    return asyncio.run(
        generate_contribution_brief_async(
            username, top_repo, alternatives, settings=settings
        )
    )
