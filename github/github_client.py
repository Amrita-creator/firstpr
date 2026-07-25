"""Read-only GitHub client for learner summaries and beginner-repo discovery."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

from models import RepositoryCandidate, SearchStrategy

load_dotenv()


class GitHubAPIError(Exception):
    """Raised when a read-only GitHub API call fails."""


class GitHubClient:
    """Thin HTTP boundary over public GitHub REST endpoints."""

    def __init__(
        self,
        token: str | None = None,
        github_api: str = "https://api.github.com",
    ):
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        self.github_api = github_api.rstrip("/")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Contribution-Compass",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.github_api}{path}"
        try:
            with httpx.Client(timeout=20) as client:
                response = client.request(
                    method, url, headers=self.headers, params=params
                )
                response.raise_for_status()
                if response.status_code == 204:
                    return None
                return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                raise GitHubAPIError(
                    "Invalid GitHub token. Please check your GITHUB_TOKEN."
                ) from exc
            if status == 403:
                raise GitHubAPIError(
                    "GitHub API rate limit exceeded or access forbidden."
                ) from exc
            if status == 404:
                raise GitHubAPIError(f"GitHub resource not found: {path}") from exc
            raise GitHubAPIError(f"GitHub API error ({status}): {exc}") from exc
        except httpx.RequestException as exc:
            raise GitHubAPIError(f"GitHub API connection error: {exc}") from exc

    def get_user_profile(self, username: str | None) -> dict[str, Any]:
        if not username or not username.strip():
            raise GitHubAPIError("Username cannot be empty or blank.")
        return self._request("GET", f"/users/{username.strip()}")

    def get_user_repo(
        self, username: str | None, page: int = 1, per_page: int = 100
    ) -> list[dict[str, Any]]:
        if not username or not username.strip():
            raise GitHubAPIError("Username cannot be empty or blank.")
        page = max(1, page)
        per_page = min(100, max(1, per_page))
        return self._request(
            "GET",
            f"/users/{username.strip()}/repos",
            params={"page": page, "per_page": per_page, "sort": "updated"},
        )

    def get_all_user_repos(self, username: str) -> list[dict[str, Any]]:
        """Fetch all repositories across pages."""
        all_repos: list[dict[str, Any]] = []
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

    def get_user_summary(self, username: str) -> dict[str, Any]:
        """Aggregate profile + repos into a compact learner summary."""
        # @lat: [[lat.md/lat#GitHub Client]]
        profile = self.get_user_profile(username)
        repos = self.get_all_user_repos(username)

        languages_count: dict[str, int] = {}
        total_stars = 0
        total_forks = 0
        total_open_issues = 0
        original_repos_count = 0
        forked_repos_count = 0
        all_topics: set[str] = set()
        latest_pushed_at = None

        for repo in repos:
            lang = repo.get("language")
            if lang:
                languages_count[lang] = languages_count.get(lang, 0) + 1

            total_stars += repo.get("stargazers_count", 0)
            total_forks += repo.get("forks_count", 0)
            total_open_issues += repo.get("open_issues_count", 0)

            if repo.get("fork"):
                forked_repos_count += 1
            else:
                original_repos_count += 1

            topics = repo.get("topics") or []
            all_topics.update(topics)

            pushed_at = repo.get("pushed_at")
            if pushed_at and (
                latest_pushed_at is None or pushed_at > latest_pushed_at
            ):
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

    def _has_path(self, full_name: str, path: str) -> bool:
        try:
            self._request("GET", f"/repos/{full_name}/contents/{path}")
            return True
        except GitHubAPIError:
            return False

    def _find_beginner_issue(
        self, full_name: str, labels: list[str]
    ) -> str | None:
        for label in labels:
            try:
                payload = self._request(
                    "GET",
                    "/search/issues",
                    params={
                        "q": f'repo:{full_name} is:issue is:open label:"{label}"',
                        "per_page": 1,
                    },
                )
            except GitHubAPIError:
                continue
            items = payload.get("items") or []
            if items:
                return items[0].get("html_url")
        return None

    def _to_candidate(
        self,
        item: dict[str, Any],
        *,
        labels: list[str],
        enrich: bool = True,
    ) -> RepositoryCandidate:
        full_name = item["full_name"]
        topics = item.get("topics") or []
        is_gsoc = any("gsoc" in topic.lower() for topic in topics)
        has_guide = False
        beginner_url = None
        if enrich:
            has_guide = self._has_path(full_name, "CONTRIBUTING.md") or self._has_path(
                full_name, ".github/CONTRIBUTING.md"
            )
            beginner_url = self._find_beginner_issue(full_name, labels)

        return RepositoryCandidate(
            name=item.get("name") or full_name.split("/")[-1],
            full_name=full_name,
            html_url=item.get("html_url") or f"https://github.com/{full_name}",
            description=item.get("description"),
            primary_language=item.get("language"),
            topics=topics,
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            open_issues_count=int(item.get("open_issues_count") or 0),
            has_contributing_guide=has_guide,
            has_beginner_issues=bool(beginner_url),
            beginner_issue_url=beginner_url,
            latest_push_date=item.get("pushed_at"),
            is_gsoc_project=is_gsoc,
            gsoc_tag="gsoc" if is_gsoc else None,
        )

    def search_beginner_repositories(
        self,
        strategy: SearchStrategy,
        *,
        limit: int = 20,
        enrich: bool = True,
    ) -> list[RepositoryCandidate]:
        """Search public repos that look suitable for a first contribution."""
        labels = strategy.recommended_labels or ["good-first-issue"]
        parts = [
            f"language:{strategy.primary_language}",
            f"stars:{strategy.min_stars}..{strategy.max_stars}",
            "archived:false",
            "is:public",
        ]
        for topic in strategy.search_topics[:3]:
            safe = topic.strip().replace(" ", "-")
            if safe:
                parts.append(f"topic:{safe}")
        # Prefer repos that advertise beginner issues in search ranking.
        query = " ".join(parts) + " good-first-issues:>0"

        payload = self._request(
            "GET",
            "/search/repositories",
            params={
                "q": query,
                "sort": "stars",
                "order": "asc",
                "per_page": min(limit, 30),
            },
        )
        items = payload.get("items") or []
        if not items:
            # Broader fallback without topic filters.
            fallback_q = (
                f"language:{strategy.primary_language} "
                f"stars:{strategy.min_stars}..{strategy.max_stars} "
                "archived:false is:public"
            )
            payload = self._request(
                "GET",
                "/search/repositories",
                params={
                    "q": fallback_q,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": min(limit, 30),
                },
            )
            items = payload.get("items") or []

        candidates: list[RepositoryCandidate] = []
        for item in items[:limit]:
            candidates.append(
                self._to_candidate(item, labels=labels, enrich=enrich)
            )
        return candidates


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


