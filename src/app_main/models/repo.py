from __future__ import annotations

from dataclasses import dataclass, field


def make_repo_key(project_name: str, repo_path: str) -> str:
    return f"{project_name}::{repo_path}"


@dataclass
class CommitInfo:
  """单条提交摘要。"""

  hash: str
  author: str
  committed_at: int
  subject: str


@dataclass
class DiscoveredRepo:
  """清单展开后的本地仓库条目。"""

  project_name: str
  repo_path: str
  local_path: str
  gerrit_base: str | None
  gerrit_project: str
  remote_name: str = "origin"
  upstream: str | None = None
  reachable: bool = True

  @property
  def repo_key(self) -> str:
    return make_repo_key(self.project_name, self.repo_path)


@dataclass
class RepoSnapshot:
  """对外展示的仓库状态。"""

  repo_key: str
  project_name: str
  repo_path: str
  status: str
  last_commit_hash: str | None
  last_commit_time: int | None
  last_commit_subject: str | None
  last_commit_author: str | None
  gerrit_base: str | None
  gerrit_project: str | None
  gerrit_project_url: str | None
  gerrit_commit_url: str | None
  gerrit_change_number: int | None
  error_message: str | None
  subscribed: bool = False
  recent_commits: list[CommitInfo] = field(default_factory=list)
  ai_summary: str | None = None
  ai_summary_status: str | None = None
  ai_summary_commit_hash: str | None = None
