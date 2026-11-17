from __future__ import annotations

import os
import time
import uuid
from collections import Counter, defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from .ai_review import AIReviewError, review_with_gemini
from .analyzer import analyze_files
from .github_client import GitHubError, fetch_repository

app = FastAPI(title="SentinelReview API", version="0.2.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

reviews: dict[str, dict] = {}
MAX_FILES = max(1, min(int(os.getenv("MAX_FILES", "30")), 100))
MAX_FILE_BYTES = max(1024, min(int(os.getenv("MAX_FILE_BYTES", "102400")), 500_000))
RATE_WINDOW_SECONDS = 60
RATE_LIMIT = 6
request_buckets: dict[str, deque[float]] = defaultdict(deque)


class ReviewRequest(BaseModel):
    repository_url: HttpUrl
    use_ai: bool = False


def enforce_rate_limit(request: Request) -> None:
    address = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = request_buckets[address]
    while bucket and now - bucket[0] > RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Review limit reached. Wait one minute before trying again.")
    bucket.append(now)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "ai_available": bool(os.getenv("GEMINI_API_KEY")),
        "engine": "deterministic + optional Gemini",
    }


@app.post("/api/reviews")
async def create_review(payload: ReviewRequest, request: Request):
    enforce_rate_limit(request)
    url = str(payload.repository_url)
    try:
        repo = await fetch_repository(url, MAX_FILES, MAX_FILE_BYTES)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GitHubError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retrieve the public repository from GitHub.") from None

    findings = analyze_files(repo["files"])
    ai_error = None
    ai_enabled = False
    if payload.use_ai:
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(status_code=409, detail="AI review is not configured. Add GEMINI_API_KEY to the server environment first.")
        try:
            ai_findings = await review_with_gemini(repo["files"])
            findings.extend(ai_findings)
            ai_enabled = True
        except AIReviewError as exc:
            # Keep deterministic results useful when the optional provider is unavailable.
            ai_error = str(exc)

    counts = Counter(item["severity"] for item in findings)
    review_id = str(uuid.uuid4())
    result = {
        "id": review_id,
        "repository": repo["name"],
        "repository_url": repo["html_url"],
        "branch": repo["branch"],
        "files_analyzed": len(repo["files"]),
        "ai_enabled": ai_enabled,
        "ai_error": ai_error,
        "summary": {
            "total": len(findings),
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
        },
        "findings": findings,
    }
    reviews[review_id] = result
    return result


@app.get("/api/reviews/{review_id}")
async def get_review(review_id: str):
    result = reviews.get(review_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Review not found. Review history is currently kept only while this server process is running.",
        )
    return result


frontend_dist = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
