"""
Purpose
    Choose and explain which GitHub repositories best fit a learner's first
    open-source contribution.
Why this file exists
    Ranking is a deterministic product decision, not a responsibility to leave
    entirely to a language model. It should be transparent and testable.
Responsibility
    Evaluate candidates using clear rules such as skill match, contribution-guide
    availability, beginner issue presence, repository activity, and scope fit.
    It must not perform HTTP requests, print output, or construct an Agno agent.
Implement
    Later create a function conceptually named `rank_repositories(profile,
    candidates)`. It should return candidates paired with OpportunityScore values
    in highest-first order, along with short human-readable reasons.
Interacts with
    Imports models from `models.py`. Receives candidates retrieved by
    `github/github_client.py`. `main.py` passes its result to `agent/mentor.py`.
    A future test file will test this module without GitHub or Agno.
Inputs
    One LearnerProfile and a list of RepositoryCandidate objects.
Outputs
    A ranked, deterministic list of score-backed opportunities.
Concepts to practice
    Pure functions, sorting, conditionals, score ranges, business rules, and
    separating deterministic code from LLM reasoning.
Common beginner mistakes
    Letting the LLM decide the score, using hidden magic numbers, mixing HTTP
    calls with ranking, or treating a high star count as beginner friendliness.
"""
