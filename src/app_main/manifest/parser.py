from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from app_main.models.repo import DiscoveredRepo


@dataclass
class _RemoteInfo:
    fetch: str = ""
    review: str = ""


def resolve_manifest_path(workspace: Path) -> Path | None:
    """定位当前活动的 repo 清单文件。"""
    repo_dir = workspace / ".repo"
    if not repo_dir.is_dir():
        return None
    manifest = repo_dir / "manifest.xml"
    if manifest.is_file():
        return manifest
    return None


def discover_project_repos(
    project_name: str,
    workspace: Path,
    fallback_gerrit: str | None,
) -> tuple[list[DiscoveredRepo], str | None]:
    """从 repo 工作区展开子仓库列表。

    Returns:
        仓库列表与项目级错误信息（无错误时为 None）。
    """
    manifest_path = resolve_manifest_path(workspace)
    if manifest_path is None:
        return [], f"缺少 .repo 目录: {workspace}"

    try:
        root = ET.parse(manifest_path).getroot()
    except ET.ParseError as exc:
        return [], f"清单解析失败: {exc}"

    remotes: dict[str, _RemoteInfo] = {}
    default_remote = "origin"
    default_revision: str | None = None

    for node in root:
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag == "remote":
            name = node.attrib.get("name", "origin")
            remotes[name] = _RemoteInfo(
                fetch=node.attrib.get("fetch", ""),
                review=node.attrib.get("review", ""),
            )
        elif tag == "default":
            default_remote = node.attrib.get("remote", default_remote)
            default_revision = node.attrib.get("revision")

    repos: list[DiscoveredRepo] = []
    for node in root:
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag != "project":
            continue
        gerrit_project = node.attrib.get("name", "")
        repo_path = node.attrib.get("path") or gerrit_project
        remote_name = node.attrib.get("remote", default_remote)
        upstream = node.attrib.get("upstream") or node.attrib.get("revision") or default_revision
        remote = remotes.get(remote_name, _RemoteInfo())
        gerrit_base = _pick_gerrit_base(remote.review, fallback_gerrit)
        local_path = workspace / repo_path
        reachable = local_path.is_dir() and (local_path / ".git").exists()
        repos.append(
            DiscoveredRepo(
                project_name=project_name,
                repo_path=repo_path,
                local_path=str(local_path),
                gerrit_base=gerrit_base,
                gerrit_project=gerrit_project,
                remote_name=remote_name,
                upstream=upstream,
                reachable=reachable,
            )
        )
    return repos, None


def _pick_gerrit_base(review: str, fallback: str | None) -> str | None:
    if review:
        return normalize_gerrit_base(review)
    if fallback:
        return normalize_gerrit_base(fallback)
    return None


def normalize_gerrit_base(value: str) -> str:
    """把 review 字段或配置 URL 规范为 https 根地址。"""
    text = value.strip().rstrip("/")
    if not text:
        return text
    if "://" not in text:
        text = f"https://{text}"
    if text.endswith("/gerrit"):
        return text
    # host/path 形式如 review.example.com/gerrit
    parts = text.split("://", 1)
    if len(parts) == 2 and "/gerrit" in parts[1]:
        return text
    return text
