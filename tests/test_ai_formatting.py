from __future__ import annotations

from app_main.ai.formatting import ai_summary_to_html, ai_summary_to_plain
from app_main.mail.sender import _build_html_body, _build_text_body
from app_main.models.repo import CommitInfo, RepoSnapshot


def test_ai_summary_to_html_renders_lists_and_headings() -> None:
    text = "### 功能变更\n- 新增登录重试\n- 调整超时"
    html = ai_summary_to_html(text)
    assert "<h3>" in html
    assert "<ul>" in html
    assert "<li>" in html
    assert "新增登录重试" in html


def test_ai_summary_to_plain_strips_markup() -> None:
    text = "### 缺陷修复\n- 修复空指针"
    plain = ai_summary_to_plain(text)
    assert "缺陷修复" in plain
    assert "修复空指针" in plain
    assert "<" not in plain


def test_email_html_includes_rendered_summary() -> None:
    repo = RepoSnapshot(
        repo_key="k",
        project_name="proj",
        repo_path="a/b",
        status="ok",
        last_commit_hash="abc",
        last_commit_time=1,
        last_commit_subject="subj",
        last_commit_author="alice",
        gerrit_base=None,
        gerrit_project=None,
        gerrit_project_url=None,
        gerrit_commit_url=None,
        gerrit_change_number=None,
        error_message=None,
    )
    commits = [
        CommitInfo(hash="abc123", author="alice", committed_at=1, subject="fix"),
    ]
    summary = "### 功能变更\n- 优化查询"
    html = _build_html_body(repo, commits, summary)
    assert "<h3>" in html
    assert "<li>" in html
    assert "优化查询" in html
    assert "### 功能变更" not in html

    text = _build_text_body(repo, commits, summary)
    assert "优化查询" in text
    assert "<li>" not in text
