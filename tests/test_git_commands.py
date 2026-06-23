from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app_main.git.commands import (
    GitError,
    UpstreamRefError,
    _collect_upstream_ref_attempts,
    local_ref_to_ls_remote_spec,
    probe_remote_unchanged,
    read_head_commit,
    resolve_upstream_ref,
    run_git,
)


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
    ref, index = resolve_upstream_ref(repo, remote="origin", upstream="master")
    assert ref in {"origin/master", "refs/remotes/origin/master"}
    assert index == 0


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
    ref, index = resolve_upstream_ref(repo, remote="origin", upstream="master")
    assert ref in {"origin/master", "refs/remotes/origin/master"}
    assert index == 0


def test_resolve_upstream_failure_lists_attempts(tmp_path: Path) -> None:
    repo = tmp_path / "bare-local"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    with pytest.raises(UpstreamRefError) as excinfo:
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
    commit_hash, commit_time, subject, author, index = read_head_commit(
        repo,
        remote="origin",
        upstream="main",
    )
    assert len(commit_hash) == 40
    assert commit_time > 0
    assert subject == "init"
    assert author == "t"
    assert index == 0


def test_resolve_upstream_sticky_start_index(tmp_path: Path) -> None:
    remote = _init_bare_remote(tmp_path)
    repo = _init_local_repo(tmp_path, remote, branch="main", set_upstream=True)
    _strip_origin_head(repo)

    strategies = _collect_upstream_ref_attempts(repo, remote="origin", upstream="missing-branch")
    fallback_index = next(
        index
        for index, attempt in enumerate(strategies)
        if attempt.label.startswith("Gerrit 常见远端分支 refs/remotes/origin/main")
    )

    ref, index = resolve_upstream_ref(
        repo,
        remote="origin",
        upstream="missing-branch",
        start_index=fallback_index,
    )
    assert ref in {"origin/main", "refs/remotes/origin/main"}
    assert index == fallback_index


def test_resolve_upstream_wraps_after_start_index(tmp_path: Path) -> None:
    remote = _init_bare_remote(tmp_path)
    repo = _init_local_repo(tmp_path, remote, branch="master", set_upstream=False)
    _strip_origin_head(repo)

    strategies = _collect_upstream_ref_attempts(repo, remote="origin", upstream="missing-branch")
    master_index = next(
        index
        for index, attempt in enumerate(strategies)
        if attempt.label.startswith("Gerrit 常见远端分支 refs/remotes/origin/master")
    )

    ref, index = resolve_upstream_ref(
        repo,
        remote="origin",
        upstream="missing-branch",
        start_index=master_index,
    )
    assert ref in {"origin/master", "refs/remotes/origin/master"}
    assert index == master_index


def test_local_ref_to_ls_remote_spec() -> None:
    assert local_ref_to_ls_remote_spec("refs/remotes/origin/master", "origin") == "refs/heads/master"
    assert local_ref_to_ls_remote_spec("origin/main", "origin") == "refs/heads/main"
    assert local_ref_to_ls_remote_spec("refs/heads/dev", "origin") == "refs/heads/dev"
    assert local_ref_to_ls_remote_spec("refs/remotes/upstream/main", "origin") is None


def test_probe_remote_unchanged_skips_fetch_when_remote_matches(tmp_path: Path, monkeypatch) -> None:
    remote = _init_bare_remote(tmp_path)
    repo = _init_local_repo(tmp_path, remote, branch="main", set_upstream=False)
    _strip_origin_head(repo)
    head_hash = run_git(repo, "rev-parse", "refs/remotes/origin/main")

    calls: list[tuple[str, ...]] = []
    original_run_git = run_git

    def tracking_run_git(repo_path: Path, *args: str, **kwargs):
        calls.append(args)
        return original_run_git(repo_path, *args, **kwargs)

    monkeypatch.setattr("app_main.git.commands.run_git", tracking_run_git)
    result = probe_remote_unchanged(
        repo,
        remote="origin",
        upstream="main",
        start_index=0,
        known_hash=head_hash,
    )
    assert result is True
    assert not any(args[0] == "fetch" for args in calls)
    assert any(args[0] == "ls-remote" for args in calls)


def test_probe_remote_unchanged_detects_remote_update(tmp_path: Path, monkeypatch) -> None:
    remote = _init_bare_remote(tmp_path)
    repo = _init_local_repo(tmp_path, remote, branch="main", set_upstream=False)
    _strip_origin_head(repo)
    known_hash = "0" * 40

    def fake_run_git(repo_path: Path, *args: str, **kwargs):
        if args[:2] == ("rev-parse",):
            return known_hash
        if args[0] == "ls-remote":
            return f"{'1' * 40}\trefs/heads/main"
        return run_git(repo_path, *args, **kwargs)

    monkeypatch.setattr("app_main.git.commands.run_git", fake_run_git)
    assert (
        probe_remote_unchanged(
            repo,
            remote="origin",
            upstream="main",
            start_index=0,
            known_hash=known_hash,
        )
        is False
    )
