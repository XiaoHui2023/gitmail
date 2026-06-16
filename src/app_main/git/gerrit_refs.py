from __future__ import annotations

import re

# Gerrit 3.x + repo 工作区常见默认分支；多数站点仍以 master 为主。
GERRIT3_REMOTE_BRANCH_FALLBACKS: tuple[str, ...] = ("master", "main", "develop")

_SHA_FULL = re.compile(r"^[0-9a-fA-F]{40}$")
_SHA_HEX = re.compile(r"^[0-9a-fA-F]+$")


def is_commit_sha(value: str) -> bool:
    """判断 manifest revision 是否为固定 commit（全量或短 hash）。"""
    text = value.strip()
    if text.startswith("refs/"):
        return False
    if _SHA_FULL.match(text):
        return True
    return 7 <= len(text) <= 40 and _SHA_HEX.match(text) is not None


def gerrit_upstream_ref_candidates(remote: str, upstream: str | None) -> list[str]:
    """把 repo manifest 的 upstream / revision 转为 fetch 后可 rev-parse 的候选引用。

    Args:
        remote: manifest remote 名（通常 origin）
        upstream: project upstream、revision 或 default revision
    """
    if not upstream:
        return []
    text = upstream.strip()
    candidates: list[str] = []

    if is_commit_sha(text):
        candidates.append(text)
    elif text.startswith("refs/tags/"):
        candidates.append(text)
    elif text.startswith("refs/heads/"):
        branch = text.removeprefix("refs/heads/")
        candidates.extend(
            (
                f"refs/remotes/{remote}/{branch}",
                f"{remote}/{branch}",
            )
        )
    elif text.startswith("refs/remotes/"):
        candidates.append(text)
    elif text.startswith("refs/"):
        candidates.append(text)
    else:
        candidates.extend(
            (
                f"refs/remotes/{remote}/{text}",
                f"{remote}/{text}",
            )
        )

    seen: set[str] = set()
    ordered: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
