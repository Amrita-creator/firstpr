"""Unit tests for deterministic repository ranking."""

from models import LearnerProfile, RepositoryCandidate, SearchStrategy
from recommender.ranker import rank_repositories


def test_ranker_prefers_language_and_beginner_signals():
    # @lat: [[lat.md/tests#Tests#Ranker prefers beginner fit]]
    profile = LearnerProfile(
        github_username="learner",
        primary_language="Python",
        skills=["python", "testing"],
        interests=["cli", "devtools"],
    )
    strategy = SearchStrategy(
        primary_language="Python",
        search_topics=["cli", "devtools"],
        min_stars=20,
        max_stars=5000,
    )
    strong = RepositoryCandidate(
        name="friendly-cli",
        full_name="org/friendly-cli",
        html_url="https://github.com/org/friendly-cli",
        description="A small CLI",
        primary_language="Python",
        topics=["cli", "devtools"],
        stars=120,
        has_contributing_guide=True,
        has_beginner_issues=True,
        beginner_issue_url="https://github.com/org/friendly-cli/issues/1",
        latest_push_date="2026-07-01T00:00:00Z",
    )
    weak = RepositoryCandidate(
        name="huge-js",
        full_name="org/huge-js",
        html_url="https://github.com/org/huge-js",
        description="Giant JS monorepo",
        primary_language="JavaScript",
        topics=["frontend"],
        stars=90000,
        has_contributing_guide=False,
        has_beginner_issues=False,
        latest_push_date="2024-01-01T00:00:00Z",
    )

    ranked = rank_repositories(profile, [weak, strong], strategy)
    assert ranked[0].repository.full_name == "org/friendly-cli"
    assert ranked[0].final_score > ranked[1].final_score
    assert ranked[0].score_reasons
