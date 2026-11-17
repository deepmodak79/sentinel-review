"""Bounded GitHub public repository reader; never follows arbitrary repository URLs."""
from __future__ import annotations

import base64
import os
import re
from urllib.parse import quote, urlparse

import httpx

OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go",
    ".rb", ".php", ".sql", ".yaml", ".yml", ".json", ".sh", ".toml",
}


class GitHubError(Exception):
    pass


def parse_repo_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter a canonical HTTPS GitHub repository URL.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or not OWNER_RE.fullmatch(parts[0]):
        raise ValueError("Use a repository URL such as https://github.com/owner/repository.")
    repo = parts[1].removesuffix(".git")
    if not REPO_RE.fullmatch(repo) or repo in {".", ".."}:
        raise ValueError("Use a valid GitHub owner/repository URL.")
    return parts[0], repo


async def fetch_repository(value: str, max_files: int, max_bytes: int) -> dict:
    owner, repo = parse_repo_url(value)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SentinelReview/0.1",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = httpx.Timeout(15.0, connect=5.0)
    async with httpx.AsyncClient(
        base_url="https://api.github.com",
        headers=headers,
        timeout=timeout,
        follow_redirects=False,
    ) as client:
        response = await client.get(f"/repos/{quote(owner)}/{quote(repo)}")
        if response.status_code == 404:
            raise GitHubError("Repository not found or not public.")
        if response.status_code in (403, 429):
            raise GitHubError("GitHub API rate limit reached. Try later or configure a server-side GITHUB_TOKEN.")
        if response.status_code >= 400:
            raise GitHubError("GitHub could not provide repository metadata.")

        metadata = response.json()
        if metadata.get("private"):
            raise GitHubError("Private repositories are not supported in this MVP.")
        branch = metadata.get("default_branch")
        if not branch:
            raise GitHubError("Repository has no default branch.")

        tree_response = await client.get(
            f"/repos/{quote(owner)}/{quote(repo)}/git/trees/{quote(branch, safe='')}",
            params={"recursive": "1"},
        )
        if tree_response.status_code >= 400:
            raise GitHubError("Could not read the repository file tree.")
        tree_payload = tree_response.json()
        if tree_payload.get("truncated"):
            raise GitHubError("Repository tree is too large for this review. Try a smaller repository.")

        max_files = max(1, min(max_files, 100))
        max_bytes = max(1024, min(max_bytes, 500_000))
        selected = []
        for entry in tree_payload.get("tree", []):
            path = entry.get("path", "")
            if entry.get("type") != "blob" or entry.get("size", max_bytes + 1) > max_bytes:
                continue
            lowered = path.lower()
            if any(part in lowered.split("/") for part in ("node_modules", "vendor", "dist", "build", ".git")):
                continue
            extension = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
            if extension in SOURCE_EXTENSIONS:
                selected.append(entry)
            if len(selected) >= max_files:
                break

        files = []
        for entry in selected:
            # Fetch blobs from the fixed API host, not arbitrary URLs supplied in tree data.
            blob = await client.get(f"/repos/{quote(owner)}/{quote(repo)}/git/blobs/{quote(entry['sha'])}")
            if blob.status_code != 200:
                continue
            data = blob.json()
            if data.get("encoding") != "base64":
                continue
            try:
                content = base64.b64decode(data.get("content", ""), validate=False).decode("utf-8", errors="replace")
            except (ValueError, UnicodeDecodeError):
                continue
            files.append({"path": entry["path"], "content": content[:max_bytes]})

    return {
        "name": metadata["full_name"],
        "html_url": metadata["html_url"],
        "branch": branch,
        "files": files,
    }
