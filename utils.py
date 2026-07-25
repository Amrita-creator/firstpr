"""
Purpose
    Hold a very small number of generic helpers that do not belong to one domain.
Why this file exists
    It prevents repeated, genuinely generic code without creating a large and
    vague utility layer.
Responsibility
    Add a helper here only when at least two unrelated files need the exact same
    simple behavior. Version 1 may not need any helper at all.
Implement
    Leave this file empty until duplication appears. A future acceptable helper
    could normalize a comma-separated skill list, but do not add it preemptively.
Interacts with
    Any module may import a proven generic helper. This file must not import the
    GitHub client, ranker, Agno mentor, or main program.
Inputs
    Small primitive values such as strings or lists, never application services.
Outputs
    Small transformed values with no network, filesystem, or model side effects.
Concepts to practice
    Pure functions, code duplication, cohesion, and resisting premature reuse.
Common beginner mistakes
    Turning this into a dumping ground, hiding business rules here, or creating
    helpers before two real callers exist.
"""
