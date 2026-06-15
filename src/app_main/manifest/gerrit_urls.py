from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from app_main.manifest.parser import normalize_gerrit_base


@dataclass
class GerritUrls:
    project_url: str | None
    commit_url: str | None


def build_gerrit_urls(
    gerrit_base: str | None,
    gerrit_project: str | None,
    commit_hash: str | None,
) -> GerritUrls:
    if not gerrit_base:
        return GerritUrls(None, None)
    base = normalize_gerrit_base(gerrit_base).rstrip("/")
    project_url = None
    commit_url = None
    if gerrit_project:
        encoded = quote(gerrit_project, safe="")
        project_url = f"{base}/#/admin/projects/{encoded}"
    if commit_hash:
        commit_url = f"{base}/q/{commit_hash}"
    return GerritUrls(project_url=project_url, commit_url=commit_url)


def gerrit_base_from_remote_url(remote_url: str) -> str | None:
    """从 git remote URL 推断 Gerrit 站点根。"""
    url = remote_url.strip()
    if not url:
        return None
    if url.startswith("git@"):
        host = url.split("@", 1)[1].split(":", 1)[0]
        return normalize_gerrit_base(host)
    if "://" in url:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.hostname:
            return normalize_gerrit_base(parsed.hostname)
    return None
