# SentinelReview

**AI-assisted code review and security analysis, with deterministic checks that work even without an AI key.**

SentinelReview accepts a GitHub repository URL and reviews its latest commit using GitHub's public API. It combines deterministic checks for common risky patterns with an optional Gemini-powered review. Findings include severity, file, line, evidence, and a practical recommendation.

## Architecture

- **Frontend:** React, TypeScript, Vite
- **API:** Python, FastAPI
- **Analysis:** deterministic rule engine + optional Gemini
- **Deployment:** one Docker image; FastAPI serves the built frontend and API
- **CI:** GitHub Actions

## Run locally

Requirements: Python 3.11+, Node 20+, npm.

1. Copy `.env.example` to `.env` and optionally add a Gemini key.
2. Start the API:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
3. Start the frontend in another terminal:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. Open http://localhost:5173. Vite proxies `/api` to the local API.

## Environment

| Variable | Purpose | Required |
|---|---|---|
| `GEMINI_API_KEY` | Enables AI-assisted review | No |
| `GEMINI_MODEL` | Gemini model name; defaults to `gemini-2.5-flash` | No |
| `GITHUB_TOKEN` | Raises GitHub API rate limits for public repos | No |
| `MAX_FILES` | Maximum source files analyzed (default 30) | No |
| `MAX_FILE_BYTES` | Per-file size limit (default 100 KB) | No |
| `CORS_ORIGINS` | Comma-separated allowed origins | No |

Never commit secrets. Configure them in the deployment platform's environment settings.

## Scope and security

- MVP supports **public GitHub repositories only**.
- It uses GitHub's HTTPS API; it does not clone repositories or accept arbitrary fetch URLs.
- File count, file size, and source extensions are bounded.
- Findings are advisory, not proof of exploitability. Review recommendations before applying them.
- No automatic code changes, commits, or merges.
- Do not submit employer/customer source code unless you have explicit authorization.

## API

- `GET /api/health` — service health and AI availability
- `POST /api/reviews` — analyze a public repository
- `GET /api/reviews/{review_id}` — retrieve an in-memory review from this process

Review history is currently process-local and resets on restart. Persistent storage is a planned follow-up, not claimed functionality.

## Deploy

Build and run with Docker:

```bash
docker build -t sentinelreview .
docker run --rm -p 8000:8000 sentinelreview
```

On Railway, connect the repository and set the service's Dockerfile path to the repository root (default). The container listens on the port provided by Railway. Add `GEMINI_API_KEY` yourself in Railway when ready.

## License

MIT
