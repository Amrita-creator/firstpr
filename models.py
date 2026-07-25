from typing import List, Optional

from pydantic import BaseModel, Field


class LearnerProfile(BaseModel):
    github_username: Optional[str] = None
    primary_language: Optional[str] = None
    secondary_languages: List[str] = []
    skills: List[str] = []
    interests: List[str] = []
    timezone: Optional[str] = None
    hours_per_week: Optional[int] = None
    interested_in_gsoc: bool = False


class RepositoryCandidate(BaseModel):
    name: str
    full_name: str
    html_url: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    topics: List[str] = []
    stars: int = 0
    forks: int = 0
    open_issues_count: int = 0
    has_contributing_guide: bool = False
    has_beginner_issues: bool = False
    beginner_issue_url: Optional[str] = None
    latest_push_date: Optional[str] = None
    is_gsoc_project: bool = False
    gsoc_tag: Optional[str] = None


class OpportunityScore(BaseModel):
    repository: RepositoryCandidate
    rank: int
    final_score: float
    matching_skills: List[str] = []
    score_reasons: List[str] = []


class MentorBriefDraft(BaseModel):
    """LLM-only fields assembled into ContributionBrief in application code."""

    # @lat: [[lat.md/lat#Domain Models]]
    why_this_is_a_match: List[str] = Field(min_length=1)
    suggested_first_steps: List[str] = Field(min_length=1)


class ContributionBrief(BaseModel):
    learner_username: Optional[str] = None
    top_recommendation: RepositoryCandidate
    alternative_options: List[RepositoryCandidate] = []
    why_this_is_a_match: List[str]
    suggested_first_steps: List[str]


class SearchStrategy(BaseModel):
    primary_language: str
    search_topics: List[str] = []
    recommended_labels: List[str] = ["good-first-issue"]
    min_stars: int = 20
    max_stars: int = 5000
    require_gsoc: bool = False
