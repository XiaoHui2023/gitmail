from __future__ import annotations

from app_main.manifest.gerrit_urls import build_gerrit_urls


def test_build_gerrit_urls_project_gerrit3_style() -> None:
    urls = build_gerrit_urls(
        "https://review.example.com/gerrit",
        "CVD/src/module/sram_wrapper",
        None,
    )
    assert urls.project_url == (
        "https://review.example.com/gerrit/c/CVD/src/module/sram_wrapper/+/"
    )
    assert urls.commit_url is None


def test_build_gerrit_urls_commit_query() -> None:
    urls = build_gerrit_urls(
        "https://review.example.com",
        "platform/build",
        "abc123def",
    )
    assert urls.project_url == "https://review.example.com/c/platform/build/+/"
    assert urls.commit_url == "https://review.example.com/q/abc123def"


def test_build_gerrit_urls_no_base() -> None:
    urls = build_gerrit_urls(None, "foo/bar", "abc")
    assert urls.project_url is None
    assert urls.commit_url is None
