from __future__ import annotations

import re
import subprocess
from pathlib import Path

from app_main.git.gerrit_refs import GERRIT3_REMOTE_BRANCH_FALLBACKS, gerrit_upstream_ref_candidates
from app_main.manifest.gerrit_urls import gerrit_base_from_remote_url
from app_main.models.repo import CommitInfo


class GitError(RuntimeError):
    pass


def _format_git_failure(repo_path: Path, args: tuple[str, ...], proc: subprocess.CompletedProcess[str]) -> str:
    stderr = proc.stderr.strip()
    stdout = proc.stdout.strip()
    parts = [
        f"git -C {repo_path} {' '.join(args)}",
        f"exit {proc.returncode}",
    ]
    if stderr:
        parts.append(f"stderr: {stderr}")
    if stdout:
        parts.append(f"stdout: {stdout}")
    if not stderr and not stdout:
        parts.append("无 stderr/stdout 输出")
    return "; ".join(parts)


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
        raise GitError(f"git 超时: git -C {repo_path} {' '.join(args)}") from exc
    if proc.returncode != 0:
        raise GitError(_format_git_failure(repo_path, args, proc))
    return proc.stdout.strip()


def git_fetch(repo_path: Path, remote: str = "origin") -> None:
    run_git(repo_path, "fetch", "--quiet", remote, "--prune")


def _try_git_ref(repo_path: Path, label: str, *args: str) -> tuple[str | None, str | None]:
    try:
        return run_git(repo_path, *args), None
    except GitError as exc:
        return None, f"{label}: {exc}"


def resolve_upstream_ref(
    repo_path: Path,
    *,
    remote: str = "origin",
    upstream: str | None = None,
) -> str:
    """解析用于对比 Gerrit 远端尖端的引用（repo manifest 优先）。

    Args:
        repo_path: 本地仓库根目录
        remote: manifest 中的 remote 名
        upstream: manifest 中的 upstream / revision 提示
    """
    attempts: list[str] = []

    for candidate in gerrit_upstream_ref_candidates(remote, upstream):
        verified, err = _try_git_ref(
            repo_path,
            f"manifest revision -> {candidate}",
            "rev-parse",
            "--verify",
            candidate,
        )
        if verified:
            return candidate
        if err:
            attempts.append(err)

    tracking, err = _try_git_ref(
        repo_path,
        "@{u}",
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )
    if tracking:
        return tracking
    if err:
        attempts.append(err)

    remote_head, err = _try_git_ref(
        repo_path,
        f"refs/remotes/{remote}/HEAD",
        "symbolic-ref",
        "-q",
        f"refs/remotes/{remote}/HEAD",
    )
    if remote_head:
        return remote_head
    if err:
        attempts.append(err)

    for branch in GERRIT3_REMOTE_BRANCH_FALLBACKS:
        candidate = f"refs/remotes/{remote}/{branch}"
        verified, err = _try_git_ref(
            repo_path,
            f"Gerrit 常见远端分支 {candidate}",
            "rev-parse",
            "--verify",
            candidate,
        )
        if verified:
            return candidate
        if err:
            attempts.append(err)

    detail = "\n  ".join(attempts) if attempts else "无可用回退"
    raise GitError(
        f"无法解析 Gerrit 远端跟踪引用 (repo={repo_path}, remote={remote}, upstream={upstream!r}):\n  {detail}"
    )


def read_head_commit(
    repo_path: Path,
    ref: str | None = None,
    *,
    remote: str = "origin",
    upstream: str | None = None,
) -> tuple[str, int, str, str]:
    target = ref or resolve_upstream_ref(repo_path, remote=remote, upstream=upstream)
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
