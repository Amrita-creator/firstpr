import os
import sys
from dotenv import load_dotenv

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from github.github_client import GitHubClient
from agent.mentor import analyze_profile_for_search, generate_contribution_brief
from models import RepositoryCandidate

def test_functions():
    username = "amrita-creator"

    # 1. Test GitHubClient.get_user_summary
    print("1. Testing GitHubClient.get_user_summary()...")
    client = GitHubClient()
    summary = client.get_user_summary(username)
    print("Summary:", summary)

    # 2. Test analyze_profile_for_search
    print("\n2. Testing analyze_profile_for_search()...")
    strategy = analyze_profile_for_search(summary)
    print("Strategy:", strategy)

    # 3. Test generate_contribution_brief
    print("\n3. Testing generate_contribution_brief()...")
    repo = RepositoryCandidate(
        name="DeepFaceCCTV",
        full_name=f"{username}/DeepFaceCCTV",
        html_url=f"https://github.com/{username}/DeepFaceCCTV",
        description="Real-time face detection & CCTV analytics.",
        primary_language=strategy.primary_language,
        topics=strategy.search_topics,
        stars=100
    )
    brief = generate_contribution_brief(username=username, top_repo=repo, alternatives=[])
    print("Brief:", brief)

if __name__ == "__main__":
    test_functions()
