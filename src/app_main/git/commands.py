from __future__ import annotations

import re
import subprocess
from pathlib import Path

from app_main.manifest.gerrit_urls import gerrit_base_from_remote_url
from app_main.models.repo import CommitInfo


class GitError(RuntimeError):
    pass


def run_git(repo_path: Path, *args: str, timeout: int = 120) -> str:
    """在仓库目录执行 git 子命令。"""
    cmd = ["git", "-C", str(repo_path), *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git 超时: {' '.join(args)}") from exc
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip()
        raise GitError(stderr or f"git 失败: {' '.join(args)}")
    return proc.stdout.strip()


def git_fetch(repo_path: Path, remote: str = "origin") -> None:
    run_git(repo_path, "fetch", "--quiet", remote, "--prune")


def resolve_upstream_ref(repo_path: Path) -> str:
    try:
        return run_git(repo_path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    except GitError:
        head = run_git(repo_path, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
        return head


def read_head_commit(repo_path: Path, ref: str | None = None) -> tuple[str, int, str, str]:
    target = ref or resolve_upstream_ref(repo_path)
    commit_hash = run_git(repo_path, "rev-parse", target)
    meta = run_git(
        repo_path,
        "log",
        "-1",
        "--format=%an|%at|%s",
        commit_hash,
    )
    author, ts_text, subject = meta.split("|", 2)
    return commit_hash, int(ts_text), subject, author


def read_recent_commits(
    repo_path: Path,
    old_hash: str | None,
    new_hash: str,
    limit: int = 5,
) -> list[CommitInfo]:
    range_spec = f"{old_hash}..{new_hash}" if old_hash and old_hash != new_hash else new_hash
    try:
        output = run_git(
            repo_path,
            "log",
            f"-{limit}",
            "--format=%H|%an|%at|%s",
            range_spec,
        )
    except GitError:
        output = run_git(
            repo_path,
            "log",
            "-1",
            "--format=%H|%an|%at|%s",
            new_hash,
        )
    commits: list[CommitInfo] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        h, author, ts_text, subject = line.split("|", 3)
        commits.append(
            CommitInfo(hash=h, author=author, committed_at=int(ts_text), subject=subject)
        )
    return commits


def read_remote_url(repo_path: Path, remote: str = "origin") -> str | None:
    try:
        return run_git(repo_path, "remote", "get-url", remote)
    except GitError:
        return None


def enrich_gerrit_base(repo_path: Path, current: str | None, remote: str = "origin") -> str | None:
    if current:
        return current
    remote_url = read_remote_url(repo_path, remote)
    if not remote_url:
        return None
    return gerrit_base_from_remote_url(remote_url)
