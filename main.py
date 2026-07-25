"""CLI entrypoint for Contribution Compass."""

from __future__ import annotations

import utils.transport
import utils.session
import argparse
import sys

from agent.mentor import (
    MentorProviderError,
    analyze_profile_for_search,
    generate_contribution_brief,
)
from config import get_settings
from github.github_client import GitHubAPIError, GitHubClient
from models import LearnerProfile
from recommender.ranker import rank_repositories


def _profile_from_summary(summary: dict) -> LearnerProfile:
    languages = summary.get("languages") or {}
    sorted_langs = sorted(languages.items(), key=lambda item: item[1], reverse=True)
    primary = sorted_langs[0][0] if sorted_langs else None
    secondary = [name for name, _ in sorted_langs[1:4]]
    return LearnerProfile(
        github_username=summary.get("username"),
        primary_language=primary,
        secondary_languages=secondary,
        skills=list(languages.keys())[:8],
        interests=list(summary.get("topics") or [])[:12],
    )


def _print_brief(brief) -> None:
    top = brief.top_recommendation
    print("\n=== Top recommendation ===")
    print(f"{top.full_name}  ({top.html_url})")
    if top.description:
        print(top.description)
    print("\nWhy this is a match:")
    for reason in brief.why_this_is_a_match:
        print(f"  - {reason}")
    print("\nSuggested first steps:")
    for step in brief.suggested_first_steps:
        print(f"  - {step}")
    if brief.alternative_options:
        print("\nAlternatives:")
        for alt in brief.alternative_options:
            print(f"  - {alt.full_name} ({alt.html_url})")


def run(username: str, *, enrich: bool = True) -> int:
    """Run the end-to-end recommendation flow for one GitHub username."""
    # @lat: [[lat.md/lat#CLI Flow]]
    settings = get_settings()
    client = GitHubClient(
        token=settings.github_token,
        github_api=settings.github_api_url,
    )

    print(f"Fetching GitHub summary for {username!r}...")
    summary = client.get_user_summary(username)
    profile = _profile_from_summary(summary)

    print(
        f"Building search strategy via Antigravity "
        f"({settings.model_provider})..."
    )
    strategy = analyze_profile_for_search(summary, settings=settings)
    print(
        f"Strategy: language={strategy.primary_language}, "
        f"topics={strategy.search_topics}, "
        f"stars={strategy.min_stars}..{strategy.max_stars}"
    )

    print("Searching beginner-friendly repositories...")
    candidates = client.search_beginner_repositories(
        strategy,
        limit=settings.search_result_limit,
        enrich=enrich,
    )
    if not candidates:
        print("No repositories found for this strategy.", file=sys.stderr)
        return 1

    ranked = rank_repositories(profile, candidates, strategy)
    print("\nRanked opportunities:")
    for item in ranked[:5]:
        repo = item.repository
        print(
            f"  {item.rank}. {repo.full_name}  score={item.final_score}  "
            f"stars={repo.stars}"
        )
        for reason in item.score_reasons[:2]:
            print(f"      - {reason}")

    top = ranked[0].repository
    alternatives = [item.repository for item in ranked[1:4]]
    print("\nGenerating contribution brief...")
    brief = generate_contribution_brief(
        username=username,
        top_repo=top,
        alternatives=alternatives,
        settings=settings,
    )
    _print_brief(brief)
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Contribution Compass — find a realistic first open-source "
            "contribution from a GitHub profile."
        )
    )
    parser.add_argument(
        "username",
        nargs="?",
        help="GitHub username to analyze",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip CONTRIBUTING.md / issue enrichment (faster, less precise)",
    )
    args = parser.parse_args(argv)
    username = args.username or input("GitHub username: ").strip()
    if not username:
        print("A GitHub username is required.", file=sys.stderr)
        raise SystemExit(2)
    try:
        raise SystemExit(run(username, enrich=not args.fast))
    except (GitHubAPIError, MentorProviderError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
