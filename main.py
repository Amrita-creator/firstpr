"""
Purpose
    Start the Contribution Compass application from the command line.
Why this file exists
    A project needs one obvious entry point so a beginner can see where execution
    begins without searching through agent, GitHub, or ranking code.
Responsibility
    Orchestrate the top-level flow only: collect input, call the ranker, then ask
    the mentor to explain the chosen recommendation. Do not contain HTTP calls,
    ranking formulas, Pydantic models, prompt text, or helper implementations.
Implement
    Later create a main function and a small `if __name__ == "__main__"` block.
    Start with hard-coded temporary input while learning, then replace it with a
    few CLI questions. Keep the main function short and readable.
Interacts with
    Imports configuration from `config.py`, data models from `models.py`, the
    GitHub client, the repository ranker, and the Agno mentor.
Inputs
    Version 1 receives learner skills, interests, and weekly hours from the
    terminal or temporary example data.
Outputs
    Prints ranked opportunities and one clear first-contribution explanation.
Concepts to practice
    Program entry points, function calls, imports, control flow, and orchestration
    versus business logic.
Common beginner mistakes
    Putting every feature here, directly calling GitHub, or creating the Agno
    agent at module import time.
"""
