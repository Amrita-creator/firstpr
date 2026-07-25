"""Deterministic scoring for first-contribution repository fit."""

from __future__ import annotations

from datetime import datetime, timezone

from models import LearnerProfile, OpportunityScore, RepositoryCandidate, SearchStrategy


def _parse_push_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _language_match(
    repo: RepositoryCandidate, profile: LearnerProfile, strategy: SearchStrategy
) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    matching: list[str] = []
    score = 0.0
    target = (strategy.primary_language or profile.primary_language or "").lower()
    repo_lang = (repo.primary_language or "").lower()
    if target and repo_lang == target:
        score += 35
        matching.append(repo.primary_language or target)
        reasons.append(f"Primary language matches ({repo.primary_language}).")
    elif repo_lang and repo_lang in {lang.lower() for lang in profile.secondary_languages}:
        score += 20
        matching.append(repo.primary_language or repo_lang)
        reasons.append(f"Secondary language match ({repo.primary_language}).")
    return score, matching, reasons


def _topic_match(
    repo: RepositoryCandidate, strategy: SearchStrategy, profile: LearnerProfile
) -> tuple[float, list[str], list[str]]:
    interests = {t.lower() for t in strategy.search_topics + profile.interests + profile.skills}
    repo_topics = {t.lower() for t in repo.topics}
    overlap = sorted(interests & repo_topics)
    if not overlap:
        return 0.0, [], []
    score = min(25.0, 8.0 * len(overlap))
    return score, overlap, [f"Shared topics: {', '.join(overlap)}."]


def _star_fit(repo: RepositoryCandidate, strategy: SearchStrategy) -> tuple[float, list[str]]:
    if strategy.min_stars <= repo.stars <= strategy.max_stars:
        return 15.0, [f"Star count ({repo.stars}) is in the approachable range."]
    if repo.stars < strategy.min_stars:
        return 4.0, [f"Smaller project ({repo.stars} stars) may still be reachable."]
    return 2.0, [f"Popular project ({repo.stars} stars) may be harder for a first PR."]


def _beginner_signals(repo: RepositoryCandidate) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if repo.has_beginner_issues:
        score += 20
        reasons.append("Has beginner-friendly issues.")
    if repo.has_contributing_guide:
        score += 10
        reasons.append("Publishes a contributing guide.")
    if repo.beginner_issue_url:
        score += 5
        reasons.append("A concrete starter issue URL is available.")
    return score, reasons


def _activity_score(repo: RepositoryCandidate) -> tuple[float, list[str]]:
    pushed = _parse_push_date(repo.latest_push_date)
    if pushed is None:
        return 0.0, []
    age_days = (datetime.now(timezone.utc) - pushed).days
    if age_days <= 30:
        return 10.0, ["Recently active (pushed within 30 days)."]
    if age_days <= 90:
        return 6.0, ["Moderately active (pushed within 90 days)."]
    if age_days <= 180:
        return 2.0, ["Somewhat stale activity."]
    return 0.0, ["Little recent activity."]


def score_repository(
    repo: RepositoryCandidate,
    profile: LearnerProfile,
    strategy: SearchStrategy,
) -> tuple[float, list[str], list[str]]:
    """Return (score, matching_skills, reasons) for one candidate."""
    total = 0.0
    matching: list[str] = []
    reasons: list[str] = []

    lang_score, lang_match, lang_reasons = _language_match(repo, profile, strategy)
    total += lang_score
    matching.extend(lang_match)
    reasons.extend(lang_reasons)

    topic_score, topic_match, topic_reasons = _topic_match(repo, strategy, profile)
    total += topic_score
    matching.extend(topic_match)
    reasons.extend(topic_reasons)

    star_score, star_reasons = _star_fit(repo, strategy)
    total += star_score
    reasons.extend(star_reasons)

    beginner_score, beginner_reasons = _beginner_signals(repo)
    total += beginner_score
    reasons.extend(beginner_reasons)

    activity, activity_reasons = _activity_score(repo)
    total += activity
    reasons.extend(activity_reasons)

    if strategy.require_gsoc and repo.is_gsoc_project:
        total += 8
        reasons.append("Matches GSoC preference.")
    elif strategy.require_gsoc and not repo.is_gsoc_project:
        total -= 15
        reasons.append("Does not match required GSoC preference.")

    return total, matching, reasons


def rank_repositories(
    profile: LearnerProfile,
    candidates: list[RepositoryCandidate],
    strategy: SearchStrategy,
) -> list[OpportunityScore]:
    """Rank candidates highest-first with transparent score reasons."""
    # @lat: [[lat.md/lat#Repository Ranking]]
    scored: list[OpportunityScore] = []
    for repo in candidates:
        final_score, matching, reasons = score_repository(repo, profile, strategy)
        scored.append(
            OpportunityScore(
                repository=repo,
                rank=0,
                final_score=round(final_score, 2),
                matching_skills=matching,
                score_reasons=reasons or ["Limited signal; kept as a fallback option."],
            )
        )
    scored.sort(key=lambda item: item.final_score, reverse=True)
    for index, item in enumerate(scored, start=1):
        item.rank = index
    return scored
