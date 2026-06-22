from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app_main.git.gerrit_refs import GERRIT3_REMOTE_BRANCH_FALLBACKS, gerrit_upstream_ref_candidates
from app_main.manifest.gerrit_urls import gerrit_base_from_remote_url
from app_main.models.repo import CommitInfo


class GitError(RuntimeError):
    pass


class UpstreamRefError(GitError):
    """所有 upstream 解析策略均失败。"""


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


@dataclass(frozen=True)
class _UpstreamRefAttempt:
    label: str
    resolved_ref: str | None
    run: Callable[[], tuple[str | None, str | None]]


def _collect_upstream_ref_attempts(
    repo_path: Path,
    *,
    remote: str,
    upstream: str | None,
) -> list[_UpstreamRefAttempt]:
    attempts: list[_UpstreamRefAttempt] = []

    for candidate in gerrit_upstream_ref_candidates(remote, upstream):
        attempts.append(
            _UpstreamRefAttempt(
                label=f"manifest revision -> {candidate}",
                resolved_ref=candidate,
                run=lambda candidate=candidate: _try_git_ref(
                    repo_path,
                    f"manifest revision -> {candidate}",
                    "rev-parse",
                    "--verify",
                    candidate,
                ),
            )
        )

    attempts.append(
        _UpstreamRefAttempt(
            label="@{u}",
            resolved_ref=None,
            run=lambda: _try_git_ref(
                repo_path,
                "@{u}",
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ),
        )
    )

    remote_head_ref = f"refs/remotes/{remote}/HEAD"
    attempts.append(
        _UpstreamRefAttempt(
            label=remote_head_ref,
            resolved_ref=None,
            run=lambda: _try_git_ref(
                repo_path,
                remote_head_ref,
                "symbolic-ref",
                "-q",
                remote_head_ref,
            ),
        )
    )

    for branch in GERRIT3_REMOTE_BRANCH_FALLBACKS:
        candidate = f"refs/remotes/{remote}/{branch}"
        attempts.append(
            _UpstreamRefAttempt(
                label=f"Gerrit 常见远端分支 {candidate}",
                resolved_ref=candidate,
                run=lambda candidate=candidate: _try_git_ref(
                    repo_path,
                    f"Gerrit 常见远端分支 {candidate}",
                    "rev-parse",
                    "--verify",
                    candidate,
                ),
            )
        )

    return attempts


def resolve_upstream_ref(
    repo_path: Path,
    *,
    remote: str = "origin",
    upstream: str | None = None,
    start_index: int = 0,
) -> tuple[str, int]:
    """解析用于对比 Gerrit 远端尖端的引用（repo manifest 优先）。

    按固定顺序尝试多种解析方式；``start_index`` 指定本次优先使用的策略下标。
    若从 ``start_index`` 到末尾均失败，再从头尝试到 ``start_index - 1``，完成一整轮。

    Args:
        repo_path: 本地仓库根目录
        remote: manifest 中的 remote 名
        upstream: manifest 中的 upstream / revision 提示
        start_index: 上次成功的策略下标，下次从此处开始

    Returns:
        解析到的引用名与本次成功的策略下标。
    """
    strategies = _collect_upstream_ref_attempts(repo_path, remote=remote, upstream=upstream)
    if not strategies:
        raise UpstreamRefError(
            f"无法解析 Gerrit 远端跟踪引用 (repo={repo_path}, remote={remote}, upstream={upstream!r}):\n  无可用回退"
        )

    bounded_start = start_index % len(strategies)
    order = list(range(bounded_start, len(strategies))) + list(range(0, bounded_start))
    errors: list[str] = []

    for index in order:
        attempt = strategies[index]
        verified, err = attempt.run()
        if verified:
            return attempt.resolved_ref or verified, index
        if err:
            errors.append(err)

    detail = "\n  ".join(errors) if errors else "无可用回退"
    raise UpstreamRefError(
        f"无法解析 Gerrit 远端跟踪引用 (repo={repo_path}, remote={remote}, upstream={upstream!r}):\n  {detail}"
    )


def read_head_commit(
    repo_path: Path,
    ref: str | None = None,
    *,
    remote: str = "origin",
    upstream: str | None = None,
    start_index: int = 0,
) -> tuple[str, int, str, str, int]:
    if ref:
        target = ref
        strategy_index = start_index
    else:
        target, strategy_index = resolve_upstream_ref(
            repo_path,
            remote=remote,
            upstream=upstream,
            start_index=start_index,
        )
    commit_hash = run_git(repo_path, "rev-parse", target)
    meta = run_git(
        repo_path,
        "log",
        "-1",
        "--format=%an|%at|%s",
        commit_hash,
    )
    author, ts_text, subject = meta.split("|", 2)
    return commit_hash, int(ts_text), subject, author, strategy_index


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


def read_commit_diff(
    repo_path: Path,
    old_hash: str,
    new_hash: str,
    *,
    max_bytes: int = 400_000,
) -> str:
    """读取 old..new 区间的 unified diff；失败或空变更时返回空字符串。"""
    if not old_hash or old_hash == new_hash:
        return ""
    try:
        diff = run_git(
            repo_path,
            "diff",
            "--no-color",
            f"{old_hash}..{new_hash}",
            timeout=90,
        )
    except GitError:
        return ""
    if len(diff.encode("utf-8", errors="ignore")) > max_bytes:
        head = diff[: max_bytes // 2]
        tail = diff[-max_bytes // 4 :]
        return f"{head}\n\n…（diff 过长，已截断）\n\n{tail}"
    return diff


def enrich_gerrit_base(repo_path: Path, current: str | None, remote: str = "origin") -> str | None:
    if current:
        return current
    remote_url = read_remote_url(repo_path, remote)
    if not remote_url:
        return None
    return gerrit_base_from_remote_url(remote_url)
