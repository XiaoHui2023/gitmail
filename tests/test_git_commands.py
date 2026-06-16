from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app_main.git.commands import GitError, read_head_commit, resolve_upstream_ref, run_git


def _init_bare_remote(tmp_path: Path, name: str = "origin.git") -> Path:
    remote = tmp_path / name
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    return remote


def _init_local_repo(tmp_path: Path, remote: Path, branch: str = "main", *, set_upstream: bool = True) -> Path:
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-b", branch, str(repo)], check=True, capture_output=True)
    (repo / "README").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True, capture_output=True)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        check=True,
        capture_output=True,
        env=env,
    )
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", str(remote)],
        check=True,
        capture_output=True,
    )
    push_args = ["git", "-C", str(repo), "push", "origin", branch]
    if set_upstream:
        push_args.insert(4, "-u")
    subprocess.run(push_args, check=True, capture_output=True)
    return repo


def _strip_origin_head(repo: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "branch", "--unset-upstream"],
        check=False,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "-d", "refs/remotes/origin/HEAD"],
        check=False,
        capture_output=True,
    )


def test_run_git_error_includes_repo_and_exit_code(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    with pytest.raises(GitError) as excinfo:
        run_git(repo, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    message = str(excinfo.value)
    assert str(repo) in message
    assert "symbolic-ref -q refs/remotes/origin/HEAD" in message
    assert "exit 1" in message


def test_resolve_upstream_uses_manifest_upstream_without_origin_head(tmp_path: Path) -> None:
    remote = _init_bare_remote(tmp_path)
    repo = _init_local_repo(tmp_path, remote, branch="master", set_upstream=False)
    _strip_origin_head(repo)
    ref = resolve_upstream_ref(repo, remote="origin", upstream="master")
    assert ref in {"origin/master", "refs/remotes/origin/master"}


def test_resolve_upstream_prefers_manifest_over_local_tracking(tmp_path: Path) -> None:
    remote = _init_bare_remote(tmp_path)
    repo = _init_local_repo(tmp_path, remote, branch="master", set_upstream=True)
    subprocess.run(
        ["git", "-C", str(repo), "branch", "main"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "push", "origin", "main"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "main"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "branch", "--set-upstream-to", "origin/main", "main"],
        check=True,
        capture_output=True,
    )
    ref = resolve_upstream_ref(repo, remote="origin", upstream="master")
    assert ref in {"origin/master", "refs/remotes/origin/master"}


def test_resolve_upstream_failure_lists_attempts(tmp_path: Path) -> None:
    repo = tmp_path / "bare-local"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    with pytest.raises(GitError) as excinfo:
        resolve_upstream_ref(repo, remote="origin", upstream="missing-branch")
    message = str(excinfo.value)
    assert "无法解析 Gerrit 远端跟踪引用" in message
    assert "remote=origin" in message
    assert "upstream='missing-branch'" in message
    assert "manifest revision ->" in message


def test_read_head_commit_with_manifest_upstream(tmp_path: Path) -> None:
    remote = _init_bare_remote(tmp_path)
    repo = _init_local_repo(tmp_path, remote, branch="main", set_upstream=False)
    _strip_origin_head(repo)
    commit_hash, commit_time, subject, author = read_head_commit(
        repo,
        remote="origin",
        upstream="main",
    )
    assert len(commit_hash) == 40
    assert commit_time > 0
    assert subject == "init"
    assert author == "t"
