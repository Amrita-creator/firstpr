"""
Purpose
    Read public GitHub repository and issue information for recommendations.
Why this file exists
    GitHub is an external system with HTTP failures, rate limits, and raw JSON.
    Keeping its code behind one boundary protects the rest of the application.
Responsibility
    Perform read-only GitHub queries and convert selected response fields into
    RepositoryCandidate models. Do not calculate rankings, write to GitHub, or
    create Agno/MCP objects.
Implement
    Later create a GitHubClient class with small methods such as
    `search_beginner_repositories` and `get_repository_details`. Use timeouts,
    clear errors, and the smallest GitHub endpoints needed for Version 1.
Interacts with
    Reads credentials supplied through `config.py`; imports models from
    `models.py`; is called by `recommender/ranker.py` or `main.py` as you choose
    after deciding where discovery belongs.
Inputs
    Search terms based on learner interests and skills plus a GitHub token.
Outputs
    Normalized RepositoryCandidate objects or understandable recoverable errors.
Concepts to practice
    Classes, HTTP requests, status codes, timeouts, JSON parsing, API limits, and
    conversion from third-party data into your own data models.
Common beginner mistakes
    Returning raw JSON everywhere, hard-coding tokens, no timeout, swallowing
    errors, or adding issue comments, PR creation, or other write actions.
"""
import os
import httpx
from dotenv import load_dotenv 
load_dotenv()


class GitHubAPIError(Exception):
    """Custom exception raised for errors during GitHub API operations."""
    pass


class GitHubClient:
    def __init__(self, token : str | None = os.getenv("GITHUB_TOKEN"), github_api : str = "https://api.github.com"):
        self.token = token
        self.github_api = github_api
        self.headers = {"Accept": "application/vnd.github+json","User-Agent":"Contribution-Compass"}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
            
    def get_user_profile(self, username: str | None):
        if not username or not username.strip():
            raise GitHubAPIError("Username cannot be empty or blank.")
        
        url = f"{self.github_api}/users/{username.strip()}"
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()  
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise GitHubAPIError("Invalid GitHub token. Please check your GITHUB_TOKEN.")
            elif exc.response.status_code == 403:
                raise GitHubAPIError("GitHub API rate limit exceeded. Please try again later.")
            elif exc.response.status_code == 404:
                raise GitHubAPIError(f"GitHub user not found: '{username}'")
            else:
                raise GitHubAPIError(f"GitHub API error: {exc}")
        except httpx.RequestException as exc:
            raise GitHubAPIError(f"GitHub API connection error: {exc}")

    def get_user_repo(self, username: str | None, page: int = 1, per_page: int = 100):
        if not username or not username.strip():
            raise GitHubAPIError("Username cannot be empty or blank.")

        # Sanitize pagination parameters
        page = max(1, page)
        per_page = min(100, max(1, per_page))

        url = f"{self.github_api}/users/{username.strip()}/repos"
        params = {"page": page, "per_page": per_page}
        
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()  
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise GitHubAPIError("Invalid GitHub token. Please check your GITHUB_TOKEN.")
            elif exc.response.status_code == 403:
                raise GitHubAPIError("GitHub API rate limit exceeded. Please try again later.")
            elif exc.response.status_code == 404:
                raise GitHubAPIError(f"GitHub user not found: '{username}'")
            else:
                raise GitHubAPIError(f"GitHub API error: {exc}")
        except httpx.RequestException as exc:
            raise GitHubAPIError(f"GitHub API connection error: {exc}")

    def get_all_user_repos(self, username: str):
        """Fetches all repositories across all pages by automatically increasing page."""
        all_repos = []
        page = 1
        per_page = 100
        while True:
            repos = self.get_user_repo(username, page=page, per_page=per_page)
            if not repos:
                break
            all_repos.extend(repos)
            if len(repos) < per_page:
                break
            page += 1
        return all_repos

    def get_user_summary(self, username: str) -> dict:
        """Fetches profile and all repositories to summarize key metrics into a single dictionary."""
        profile = self.get_user_profile(username)
        repos = self.get_all_user_repos(username)

        languages_count = {}
        total_stars = 0
        total_forks = 0
        total_open_issues = 0
        original_repos_count = 0
        forked_repos_count = 0
        all_topics = set()
        latest_pushed_at = None

        for repo in repos:
            # Aggregate languages
            lang = repo.get("language")
            if lang:
                languages_count[lang] = languages_count.get(lang, 0) + 1

            # Aggregate stars, forks, and issues
            total_stars += repo.get("stargazers_count", 0)
            total_forks += repo.get("forks_count", 0)
            total_open_issues += repo.get("open_issues_count", 0)

            # Original vs Forked
            if repo.get("fork"):
                forked_repos_count += 1
            else:
                original_repos_count += 1

            # Aggregate unique topics
            topics = repo.get("topics") or []
            all_topics.update(topics)

            # Track latest push date
            pushed_at = repo.get("pushed_at")
            if pushed_at:
                if latest_pushed_at is None or pushed_at > latest_pushed_at:
                    latest_pushed_at = pushed_at

        return {
            "username": profile.get("login"),
            "name": profile.get("name"),
            "public_repos_count": profile.get("public_repos", 0),
            "retrieved_repos_count": len(repos),
            "original_repos_count": original_repos_count,
            "forked_repos_count": forked_repos_count,
            "total_stars": total_stars,
            "total_forks": total_forks,
            "total_open_issues": total_open_issues,
            "languages": languages_count,
            "topics": list(all_topics),
            "latest_push_date": latest_pushed_at,
        }


if __name__ == "__main__":
    client = GitHubClient()
    print("Testing GitHubClient.get_user_summary()...")
    try:
        summary = client.get_user_summary("ash-blanc")
        print("\nUser Profile & Repositories Summary Dictionary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
    except GitHubAPIError as err:
        print(f"GitHub API Error: {err}")


