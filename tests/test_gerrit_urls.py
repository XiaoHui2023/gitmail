from __future__ import annotations

from app_main.manifest.gerrit_urls import build_gerrit_urls, resolve_gerrit_change_number


def test_build_gerrit_urls_project_gerrit3_style() -> None:
    urls = build_gerrit_urls(
        "http://review.example.com/gerrit",
        "CVD/src/module/sram_wrapper",
        None,
        12345,
    )
    assert urls.project_url == (
        "http://review.example.com/gerrit/c/CVD/src/module/sram_wrapper/+/12345"
    )
    assert urls.commit_url is None


def test_build_gerrit_urls_commit_query_fallback() -> None:
    urls = build_gerrit_urls(
        "http://review.example.com",
        "platform/build",
        "abc123def",
    )
    assert urls.project_url == "http://review.example.com/q/abc123def"
    assert urls.commit_url == "http://review.example.com/q/abc123def"


def test_build_gerrit_urls_project_query_fallback() -> None:
    urls = build_gerrit_urls("http://review.example.com", "platform/build", None)
    assert urls.project_url == "http://review.example.com/q/project:platform%2Fbuild"
    assert urls.commit_url is None


def test_build_gerrit_urls_no_base() -> None:
    urls = build_gerrit_urls(None, "foo/bar", "abc")
    assert urls.project_url is None
    assert urls.commit_url is None


def test_resolve_gerrit_change_number(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self):
            return b")]}\'\n[{\"_number\": 6789}]"

    calls = []

    def fake_urlopen(url, timeout):
        calls.append((url, timeout))
        return FakeResponse()

    monkeypatch.setattr("app_main.manifest.gerrit_urls.urlopen", fake_urlopen)
    number = resolve_gerrit_change_number(
        "http://review.example.com",
        "platform/build",
        "abc123def",
    )
    assert number == 6789
    assert calls[0][0] == (
        "http://review.example.com/changes/?q=commit%3Aabc123def%20project%3Aplatform%2Fbuild&o=SKIP_DIFFSTAT"
    )
