from __future__ import annotations

from app_main.mail.sender import _build_html_body, _build_text_body
from app_main.models.repo import CommitInfo, RepoSnapshot


def _sample_repo() -> RepoSnapshot:
    return RepoSnapshot(
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


def test_email_includes_plain_ai_summary() -> None:
    repo = _sample_repo()
    commits = [
        CommitInfo(hash="abc123", author="alice", committed_at=1, subject="fix"),
    ]
    summary = "功能变更：\n· 优化查询\n· 调整超时"
    html = _build_html_body(repo, commits, summary)
    assert "优化查询" in html
    assert "调整超时" in html
    assert "<pre" in html
    assert "<h3>" not in html
    assert "###" not in html

    text = _build_text_body(repo, commits, summary)
    assert "优化查询" in text
    assert summary in text
