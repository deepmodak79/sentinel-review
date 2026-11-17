import pytest

from app.github_client import parse_repo_url


def test_accepts_canonical_repository_url():
    assert parse_repo_url("https://github.com/psf/requests") == ("psf", "requests")
    assert parse_repo_url("https://github.com/psf/requests.git") == ("psf", "requests")


@pytest.mark.parametrize("url", [
    "http://github.com/psf/requests",
    "https://github.com.evil.example/psf/requests",
    "https://github.com/psf/requests/issues/1",
    "https://github.com/psf/requests?tab=readme",
    "https://user:pass@github.com/psf/requests",
    "https://example.com/psf/requests",
])
def test_rejects_noncanonical_repository_urls(url):
    with pytest.raises(ValueError):
        parse_repo_url(url)
