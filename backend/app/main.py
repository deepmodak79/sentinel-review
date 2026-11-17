from __future__ import annotations

import os
import uuid
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl

from .analyzer import analyze_files
from .github_client import GitHubError, fetch_repository

app = FastAPI(title="SentinelReview API", version="0.1.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

reviews: dict[str, dict] = {}
MAX_FILES = max(1, min(int(os.getenv("MAX_FILES", "30")), 100))
MAX_FILE_BYTES = max(1024, min(int(os.getenv("MAX_FILE_BYTES", "102400")), 500_000))


class ReviewRequest(BaseModel):
    repository_url: HttpUrl


@app.get("/api/health")
async def health():
    return {"status": "ok", "ai_available": bool(os.getenv("GEMINI_API_KEY")), "engine": "deterministic + optional Gemini"}


@app.post("/api/reviews")
async def create_review(payload: ReviewRequest):
    url = str(payload.repository_url)
    try:
        repo = await fetch_repository(url, MAX_FILES, MAX_FILE_BYTES)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GitHubError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Do not leak upstream response bodies, tokens, or internal exception details.
        raise HTTPException(status_code=502, detail="Could not retrieve the public repository from GitHub.") from exc

    findings = analyze_files(repo["files"])
    counts = Counter(item["severity"] for item in findings)
    review_id = str(uuid.uuid4())
    result = {
        "id": review_id,
        "repository": repo["name"],
        "repository_url": repo["html_url"],
        "branch": repo["branch"],
        "files_analyzed": len(repo["files"]),
        "ai_enabled": False,
        "summary": {"total": len(findings), "high": counts["high"], "medium": counts["medium"], "low": counts["low"]},
        "findings": findings,
    }
    reviews[review_id] = result
    return result


@app.get("/api/reviews/{review_id}")
async def get_review(review_id: str):
    result = reviews.get(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found. Review history is currently kept only while this server process is running.")
    return result


frontend_dist = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
