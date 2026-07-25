"""
Purpose
    Configure the one Agno agent that turns a selected opportunity into an
    understandable first-contribution guide.
Why this file exists
    The LLM is valuable for explanation and tailored next steps, but it should
    not own GitHub retrieval or deterministic ranking logic.
Responsibility
    Create one OpenSourceMentor agent with strict instructions and MCP tools.
    It explains evidence already gathered and can request more read-only data;
    it must never claim to have created issues, branches, or pull requests.
Implement
    First learn Agno with one local tool. Then create a factory function such as
    `create_mentor`. Connect the agent to your local MCP server and require a
    structured ContributionBrief response. Keep prompts short and factual.
Interacts with
    Imports models from `models.py`. `main.py` calls the factory. It connects as
    an MCP client to the server you will add later; that server may initially live
    beside this file only after the core GitHub and ranking flow works.
Inputs
    Connected MCP tools, model configuration from `config.py`, learner profile,
    and selected ranked opportunity.
Outputs
    A configured Agno agent and a validated ContributionBrief when it runs.
Concepts to practice
    Agno Agents, system instructions, structured output, MCP tool calling,
    tool-result grounding, and limitations of LLM explanations.
Common beginner mistakes
    Creating several agents first, vague instructions, putting GitHub API logic
    in prompts, allowing write tools, or trusting text that lacks tool evidence.
"""
import json
from agno.agent import Agent
from agno.models.groq import Groq
from models import SearchStrategy, ContributionBrief, RepositoryCandidate

def analyze_profile_for_search(user_summary: dict) -> SearchStrategy:
    """
    Passes raw GitHub summary dictionary to an Agno agent to generate
    a structured SearchStrategy.
    """
    profiler_agent = Agent(
        model=Groq(id="llama-3.3-70b-versatile"),
        description="You are an Open Source Advisor evaluating developer GitHub profiles.",
        output_schema=SearchStrategy,
        structured_outputs=True
    )
    
    prompt = f"""
    Analyze this developer's GitHub activity summary:
    {json.dumps(user_summary, indent=2)}

    Determine their primary programming language, topics of interest, and ideal star range 
    to search for beginner/intermediate open source projects they can contribute to.
    """
    
    response = profiler_agent.run(prompt)
    return response.content


def generate_contribution_brief(
    username: str, 
    top_repo: RepositoryCandidate, 
    alternatives: list[RepositoryCandidate]
) -> ContributionBrief:
    """
    Generates a personalized ContributionBrief guide for the learner using an Agno agent.
    """
    mentor_agent = Agent(
        model=Groq(id="llama-3.3-70b-versatile"),
        description="You are a friendly open-source mentor helping a learner make their first contribution.",
        output_schema=ContributionBrief,
        structured_outputs=True
    )
    
    prompt = f"""
    Learner: {username}
    Top Recommended Repo: {top_repo.full_name} ({top_repo.html_url})
    Description: {top_repo.description}
    Language: {top_repo.primary_language}
    
    Explain why this repository is a great match and provide 3 clear, actionable first steps for contributing.
    """
    
    response = mentor_agent.run(prompt)
    return response.content
