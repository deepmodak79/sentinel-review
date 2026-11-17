# SentinelReview

**Evidence-led security review for public GitHub repositories.** SentinelReview combines deterministic static checks with optional Gemini-assisted review. Findings include severity, file, line, evidence, and a practical recommendation.

## Architecture

- **Frontend:** React, TypeScript, Vite
- **API:** Python, FastAPI
- **Analysis:** deterministic rule engine + opt-in Gemini review
- **Deployment:** one Docker image; FastAPI serves the built frontend and API
- **CI:** GitHub Actions

## Run locally

Requirements: Python 3.11+, Node 20+, npm.

1. Copy \`.env.example\` to \`.env\`.
2. Start the API:
   \`cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000\`
3. Start the frontend in another terminal:
   \`cd frontend && npm install && npm run dev\`
4. Open http://localhost:5173. Vite proxies \`/api\` to the local API.

## Environment

| Variable | Purpose | Required |
|---|---|---|
| \`GEMINI_API_KEY\` | Enables opt-in Gemini review | No |
| \`GEMINI_MODEL\` | Gemini model; defaults to \`gemini-2.5-flash\` | No |
| \`GITHUB_TOKEN\` | Raises GitHub API rate limits for public repos | No |
| \`MAX_FILES\` | Maximum source files analyzed (default 30) | No |
| \`MAX_FILE_BYTES\` | Per-file size limit (default 100 KB) | No |
| \`CORS_ORIGINS\` | Comma-separated allowed origins | No |

Never commit secrets. Configure them in the deployment platform's environment settings.

## AI review and privacy

AI review is off by default. The user must explicitly select **Include Gemini-assisted review**. When enabled, bounded source excerpts are sent to Google's Gemini API. Common credential-like assignments are redacted before sending, but redaction is heuristic and cannot guarantee removal of every secret. Do not submit confidential employer/customer source code without authorization.

## Scope and security

- Public GitHub repositories only.
- Only canonical HTTPS GitHub repository URLs are accepted.
- GitHub API requests go to the fixed \`api.github.com\` host; repository code is never cloned or executed.
- File count and file size are bounded.
- Credential-like values are redacted from deterministic finding evidence.
- Findings are advisory, not proof of exploitability. Validate every result before acting.
- No automatic code changes, commits, or merges.
- Review history is process-local and resets on restart. Persistent storage is not implemented.

## API

- \`GET /api/health\` — service health and AI availability
- \`POST /api/reviews\` — analyze a public repository (\`use_ai: true\` opts into Gemini)
- \`GET /api/reviews/{review_id}\` — retrieve a review while it remains in this process

## Deploy

Build and run with Docker:

\`docker build -t sentinelreview . && docker run --rm -p 8000:8000 sentinelreview\`

Connect the repository root to a Railway Dockerfile service. The container listens on the port provided by Railway. Add \`GEMINI_API_KEY\` yourself in Railway when ready; do not paste it into chat or commit it.

## License

MIT
