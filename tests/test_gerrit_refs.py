from __future__ import annotations

from app_main.git.gerrit_refs import (
    GERRIT3_REMOTE_BRANCH_FALLBACKS,
    gerrit_upstream_ref_candidates,
    is_commit_sha,
)


def test_is_commit_sha() -> None:
    assert is_commit_sha("a" * 40)
    assert is_commit_sha("abc1234")
    assert not is_commit_sha("master")
    assert not is_commit_sha("refs/heads/master")


def test_gerrit_upstream_ref_candidates_branch_short_name() -> None:
    refs = gerrit_upstream_ref_candidates("origin", "master")
    assert refs == ["refs/remotes/origin/master", "origin/master"]


def test_gerrit_upstream_ref_candidates_refs_heads() -> None:
    refs = gerrit_upstream_ref_candidates("origin", "refs/heads/master")
    assert refs == ["refs/remotes/origin/master", "origin/master"]


def test_gerrit_upstream_ref_candidates_pinned_sha() -> None:
    sha = "a" * 40
    assert gerrit_upstream_ref_candidates("origin", sha) == [sha]


def test_gerrit3_fallbacks_master_first() -> None:
    assert GERRIT3_REMOTE_BRANCH_FALLBACKS[0] == "master"
