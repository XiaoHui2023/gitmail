from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote, urlparse
from urllib.request import urlopen

from app_main.manifest.parser import normalize_gerrit_base


@dataclass
class GerritUrls:
    project_url: str | None
    commit_url: str | None


def build_gerrit_urls(
    gerrit_base: str | None,
    gerrit_project: str | None,
    commit_hash: str | None,
    change_number: int | None = None,
) -> GerritUrls:
    if not gerrit_base:
        return GerritUrls(None, None)
    base = normalize_gerrit_base(gerrit_base).rstrip("/")
    project_url = None
    commit_url = None
    if gerrit_project:
        project = gerrit_project.strip("/")
        if change_number:
            project_url = f"{base}/c/{project}/+/{change_number}"
        elif commit_hash:
            project_url = f"{base}/q/{commit_hash}"
        else:
            project_url = f"{base}/q/project:{quote(project, safe='')}"
    if commit_hash:
        commit_url = f"{base}/q/{commit_hash}"
    return GerritUrls(project_url=project_url, commit_url=commit_url)


def _gerrit_change_query_candidates(gerrit_project: str | None, commit_hash: str) -> list[str]:
    """Gerrit change 查询语句候选（按优先级排列）。"""
    queries: list[str] = []
    if gerrit_project:
        project = gerrit_project.strip("/")
        if project:
            queries.append(f"commit:{commit_hash} project:{project}")
    queries.append(f"commit:{commit_hash}")
    return queries


def _fetch_gerrit_change_number(base: str, query: str, timeout: int) -> int | None:
    request_url = f"{base}/changes/?q={quote(query, safe='')}&o=SKIP_DIFFSTAT"
    with urlopen(request_url, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    if raw.startswith(")]}'"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else ""
    changes = json.loads(raw)
    if not changes:
        return None
    number = changes[0].get("_number")
    return int(number) if number is not None else None


def resolve_gerrit_change_number(
    gerrit_base: str | None,
    gerrit_project: str | None,
    commit_hash: str | None,
    timeout: int = 10,
    start_index: int = 0,
) -> tuple[int | None, int]:
    """查询 commit 对应的 Gerrit change number。

    按固定顺序尝试多种查询语句；``start_index`` 为上次成功的策略下标。
    若从 ``start_index`` 到末尾均无结果，再从头尝试到 ``start_index - 1``。

    Returns:
        (change number 或 None, 本次成功的策略下标)。
    """
    if not gerrit_base or not commit_hash:
        return None, 0
    base = normalize_gerrit_base(gerrit_base).rstrip("/")
    queries = _gerrit_change_query_candidates(gerrit_project, commit_hash)
    if not queries:
        return None, 0

    bounded_start = start_index % len(queries)
    order = list(range(bounded_start, len(queries))) + list(range(0, bounded_start))
    last_index = bounded_start
    last_error: Exception | None = None

    for index in order:
        last_index = index
        try:
            number = _fetch_gerrit_change_number(base, queries[index], timeout)
        except Exception as exc:
            last_error = exc
            continue
        if number is not None:
            return number, index

    if last_error is not None:
        raise last_error
    return None, last_index


def gerrit_base_from_remote_url(remote_url: str) -> str | None:
    """从 git remote URL 推断 Gerrit 站点根。"""
    url = remote_url.strip()
    if not url:
        return None
    if url.startswith("git@"):
        host = url.split("@", 1)[1].split(":", 1)[0]
        return normalize_gerrit_base(host)
    if "://" in url:
        parsed = urlparse(url)
        if parsed.hostname:
            return normalize_gerrit_base(parsed.hostname)
    return None
