# Contribution Compass

Find a realistic first open-source contribution from a GitHub profile.

The CLI reads a learner’s public GitHub activity, asks an [Antigravity](https://antigravity.google/docs/sdk/overview) mentor for a search strategy, discovers beginner-friendly repositories (read-only), ranks them with transparent scores, and returns a concrete contribution brief.

## Setup

```bash
cp .env.example .env
uv sync          # or: pip install -e .
```

### Model provider: `bunx openai-oauth` (ChatGPT account)

```bash
bunx openai-oauth login
bunx openai-oauth --detach
bunx openai-oauth status     # copy a model id from the list
```

In `.env`:

```bash
MODEL_PROVIDER=openai-oauth
OPENAI_BASE_URL=http://127.0.0.1:10531/v1
OPENAI_MODEL=gpt-5.6-terra   # must appear in `bunx openai-oauth status`
OPENAI_API_KEY=sk-local      # dummy; local proxy ignores it
GITHUB_TOKEN=ghp_...         # recommended
```

If you see `Route not found` / 404: confirm the proxy is still running, `OPENAI_BASE_URL` ends with `/v1`, and `OPENAI_MODEL` is one of the listed ids.

### Model provider: Gemini (Antigravity default)

```bash
MODEL_PROVIDER=gemini
GEMINI_API_KEY=...
```

## Run

```bash
uv run firstpr <github-username>
# faster (skip CONTRIBUTING.md / issue enrichment):
uv run firstpr <github-username> --fast
```

Smoke-test mentor only:

```bash
uv run python tests/testing1.py
```

Unit tests (no network / no model):

```bash
uv run pytest tests/test_ranker.py
```

## Architecture

| Module | Role |
|--------|------|
| `github/github_client.py` | Read-only GitHub HTTP + candidate normalization |
| `recommender/ranker.py` | Deterministic scoring (not LLM) |
| `agent/mentor.py` | Antigravity structured-output mentors |
| `config.py` | Env validation (`gemini` / `openai-oauth`) |
| `main.py` | Orchestration CLI |

Safety: GitHub access is read-only. Mentors only expose the Antigravity `finish` tool for structured output.
