This directory defines the high-level concepts, business logic, and architecture of this project using markdown. It is managed by [lat.md](https://www.npmjs.com/package/lat.md).

- [[tests]] — Ranking unit-test specs that must stay free of GitHub and model providers

# Contribution Compass

CLI that maps a GitHub profile to a realistic first open-source contribution using read-only GitHub data, deterministic ranking, and Antigravity mentors.

Version 1 flow: profile summary → search strategy → repo discovery → ranked opportunities → contribution brief. Ranking and GitHub I/O stay outside the LLM. Agno was replaced by the Google Antigravity SDK (`google-antigravity`).

Related: [[lat.md/lat#CLI Flow]], [[lat.md/lat#Mentor Agents]], [[lat.md/lat#Repository Ranking]], and [[tests|test specs]].

# Configuration

Environment-backed settings choose the model backend and GitHub credentials without hard-coding secrets.

`[[config.py#Settings]]` is loaded once by `[[config.py#get_settings]]`. Provider resolution prefers Gemini when `GEMINI_API_KEY` / `GOOGLE_API_KEY` is set; otherwise defaults to `openai-oauth` for local ChatGPT proxy testing.

Required env by provider is validated before the CLI runs. See [[lat.md/lat#Model Providers]].

# Model Providers

Mentors use Antigravity for Gemini and the OpenAI SDK for the local ChatGPT oauth proxy.

| Provider | Runtime | Typical env |
|----------|---------|-------------|
| `gemini` | Antigravity `LocalAgentConfig` | `GEMINI_API_KEY`, optional `GEMINI_MODEL` |
| `openai-oauth` | OpenAI Chat Completions via `[[agent/mentor.py#_run_structured_openai]]` | `OPENAI_BASE_URL=http://127.0.0.1:10531/v1`, `OPENAI_MODEL`, dummy `OPENAI_API_KEY` |

`openai-oauth` is `bunx openai-oauth`. Antigravity’s `LocalOpenAIAgentConfig` is not used here — its finish-tool harness hits routes that proxy does not expose cleanly (`Route not found` 404s).

# GitHub Client

Read-only GitHub REST boundary that returns summaries and `RepositoryCandidate` lists.

`[[github/github_client.py#GitHubClient]]` aggregates a learner summary, searches beginner-friendly repos (`good-first-issues:>0` with language/topic/star filters), and optionally enriches with CONTRIBUTING.md presence and a starter issue URL. No issue comments, PRs, or other writes.

# Repository Ranking

Deterministic scoring separates product decisions from LLM prose so rankings stay testable and transparent.

`[[recommender/ranker.py#rank_repositories]]` scores each `[[models.py#RepositoryCandidate]]` into `[[models.py#OpportunityScore]]` using language match, topic overlap, star-range fit, beginner signals (guide / good-first-issue), recent push activity, and optional GSoC preference. Higher score ranks first; reasons are human-readable.

# Mentor Agents

Antigravity agents produce structured search strategy and brief prose from evidence already gathered.

Mentors expose only `BuiltinTools.FINISH` (no filesystem/shell). Strategy uses `[[models.py#SearchStrategy]]`. Brief prose uses `[[models.py#MentorBriefDraft]]`; application code then attaches repo objects into `[[models.py#ContributionBrief]]` so the model cannot invent repository fields.

Helpers: `[[agent/mentor.py#analyze_profile_for_search]]`, `[[agent/mentor.py#generate_contribution_brief]]`.

# Read-only Safety

GitHub stays read-only and mentors cannot mutate the local workspace.

GitHub client methods only GET public REST data. Mentor `CapabilitiesConfig` allowlists `finish` alone so Antigravity builtin file/shell tools are not offered to the model. The product never claims to open issues, branches, or pull requests.

# Domain Models

Pydantic models are the shared contract between GitHub, ranking, mentors, and the CLI.

Key types: `[[models.py#LearnerProfile]]`, `[[models.py#RepositoryCandidate]]`, `[[models.py#OpportunityScore]]`, `[[models.py#SearchStrategy]]`, `[[models.py#MentorBriefDraft]]`, `[[models.py#ContributionBrief]]`. Mentors return schema-bound JSON; ranking and GitHub produce/consume the same candidate shape.

# CLI Flow

The installed console script is `firstpr` (`[[main.py#main]]`); orchestration stays in `main.py`.

`[[main.py#run]]` wires settings, summary, strategy, search, rank, and brief, and supports `--fast` to skip CONTRIBUTING.md / issue enrichment. It must not embed HTTP clients, score formulas, or prompt templates inline.
