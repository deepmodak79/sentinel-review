"""GitHub public repository reader. Only accepts canonical github.com owner/repo URLs."""
from __future__ import annotations

import base64
import os
import re
from urllib.parse import urlparse

import httpx

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go", ".rb", ".php", ".sql", ".yaml", ".yml", ".json", ".sh"}


class GitHubError(Exception):
    pass


def parse_repo_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.port not in (None, 443):
        raise ValueError("Enter an HTTPS URL from github.com.")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or not REPO_RE.fullmatch(parts[0]) or not REPO_RE.fullmatch(parts[1].removesuffix(".git")):
        raise ValueError("Use a repository URL such as https://github.com/owner/repository.")
    return parts[0], parts[1].removesuffix(".git")


async def fetch_repository(value: str, max_files: int, max_bytes: int) -> dict:
    owner, repo = parse_repo_url(value)
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    timeout = httpx.Timeout(15.0, connect=5.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=False) as client:
        root = f"https://api.github.com/repos/{owner}/{repo}"
        response = await client.get(root)
        if response.status_code == 404:
            raise GitHubError("Repository not found or not public.")
        response.raise_for_status()
        metadata = response.json()
        branch = metadata.get("default_branch")
        if not branch:
            raise GitHubError("Repository has no default branch.")
        tree_response = await client.get(f"{root}/git/trees/{branch}", params={"recursive": "1"})
        tree_response.raise_for_status()
        tree = tree_response.json().get("tree", [])
        selected = []
        for entry in tree:
            path = entry.get("path", "")
            if entry.get("type") != "blob" or entry.get("size", max_bytes + 1) > max_bytes:
                continue
            ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
            if ext in SOURCE_EXTENSIONS:
                selected.append(entry)
            if len(selected) >= max_files:
                break
        files = []
        for entry in selected:
            raw = await client.get(entry["url"])
            raw.raise_for_status()
            data = raw.json()
            if data.get("encoding") != "base64":
                continue
            try:
                content = base64.b64decode(data["content"], validate=False).decode("utf-8", errors="replace")
            except (KeyError, ValueError):
                continue
            files.append({"path": entry["path"], "content": content[:max_bytes]})
        return {"name": metadata["full_name"], "html_url": metadata["html_url"], "branch": branch, "files": files}
