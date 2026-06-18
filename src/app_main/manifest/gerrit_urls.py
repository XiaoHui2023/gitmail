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


def resolve_gerrit_change_number(
    gerrit_base: str | None,
    gerrit_project: str | None,
    commit_hash: str | None,
    timeout: int = 10,
) -> int | None:
    if not gerrit_base or not gerrit_project or not commit_hash:
        return None
    base = normalize_gerrit_base(gerrit_base).rstrip("/")
    project = gerrit_project.strip("/")
    query = quote(f"commit:{commit_hash} project:{project}", safe="")
    request_url = f"{base}/changes/?q={query}&o=SKIP_DIFFSTAT"
    with urlopen(request_url, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    if raw.startswith(")]}'"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else ""
    changes = json.loads(raw)
    if not changes:
        return None
    number = changes[0].get("_number")
    return int(number) if number is not None else None


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
