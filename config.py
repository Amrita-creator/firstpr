"""
Purpose
    Centralize application configuration that comes from the environment.
Why this file exists
    Tokens and provider choices should have one documented source rather than
    being duplicated or hard-coded throughout the project.
Responsibility
    Load and validate only configuration needed by Version 1, such as a GitHub
    token and the model-provider key you select. Do not make API calls here.
Implement
    Later create a small settings model or function that reads environment
    variables once and fails with a clear message when a required value is absent.
    Keep configuration minimal; do not add a settings framework unless needed.
Interacts with
    `github/github_client.py` needs GitHub credentials. `agent/mentor.py` needs
    model-provider configuration. `main.py` may create settings and pass them on.
Inputs
    Environment variables documented in `.env.example`.
Outputs
    Validated configuration values, never printed tokens or secrets.
Concepts to practice
    Environment variables, configuration boundaries, `.env` files, validation,
    and safe error messages.
Common beginner mistakes
    Hard-coding tokens, reading environment variables in every file, logging
    secrets, or adding configuration for features that do not exist yet.
"""
GITHUB_TOKEN = "GITHUB_TOKEN"
GITHUB_API_URL = "GITHUB_API_URL"