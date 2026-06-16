from __future__ import annotations

import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from app_main.git.commands import (
    GitError,
    enrich_gerrit_base,
    git_fetch,
    read_head_commit,
    read_recent_commits,
)
from app_main.mail.notifier import Notifier
from app_main.manifest.parser import discover_project_repos
from app_main.models.config import AppConfig
from app_main.models.repo import DiscoveredRepo
from app_main.store.database import Store

logger = logging.getLogger(__name__)


@dataclass
class MonitorHealth:
    running: bool = False
    last_round_started_at: float = 0.0
    last_round_finished_at: float = 0.0
    last_round_seconds: float = 0.0
    last_round_repo_count: int = 0
    failed_repo_count: int = 0
    project_errors: dict[str, str] = field(default_factory=dict)


class MonitorService:
    """后台仓库监控调度。"""

    def __init__(self, config: AppConfig, store: Store, notifier: Notifier) -> None:
        self._config = config
        self._store = store
        self._notifier = notifier
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._repos: list[DiscoveredRepo] = []
        self._manifest_mtime: dict[str, float] = {}
        self._last_manifest_refresh = 0.0
        self.health = MonitorHealth()
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="gitmail-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def list_repos(self) -> list[DiscoveredRepo]:
        with self._lock:
            return list(self._repos)

    def _loop(self) -> None:
        self.health.running = True
        while not self._stop.is_set():
            try:
                self._run_round()
            except Exception as exc:
                logger.exception("监控轮次异常: %s", exc)
            self.health.failed_repo_count = self._store.count_failed_repos()
            wait = max(5, self._config.poll_interval_seconds)
            if self._stop.wait(wait + random.uniform(0, 3)):
                break
        self.health.running = False

    def _run_round(self) -> None:
        started = time.time()
        self.health.last_round_started_at = started
        self._refresh_registry()
        repos = self.list_repos()
        self.health.last_round_repo_count = len(repos)
        if not repos:
            self.health.last_round_finished_at = time.time()
            self.health.last_round_seconds = self.health.last_round_finished_at - started
            return
        concurrency = max(1, self._config.fetch_concurrency)
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(self._check_repo, repo) for repo in repos]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    logger.warning("仓库检查任务异常: %s", exc)
        finished = time.time()
        self.health.last_round_finished_at = finished
        self.health.last_round_seconds = finished - started

    def _refresh_registry(self) -> None:
        now = time.time()
        force = (now - self._last_manifest_refresh) >= self._config.manifest_refresh_seconds

        for project in self._config.projects:
            manifest = Path(project.workspace).expanduser() / ".repo" / "manifest.xml"
            if manifest.is_file():
                mtime = manifest.stat().st_mtime
                prev = self._manifest_mtime.get(project.name)
                if prev is not None and mtime != prev:
                    force = True
                self._manifest_mtime[project.name] = mtime

        if not force and self._repos:
            return

        all_repos: list[DiscoveredRepo] = []
        project_errors: dict[str, str] = {}
        active_keys: set[str] = set()

        for project in self._config.projects:
            workspace = Path(project.workspace).expanduser()
            repos, err = discover_project_repos(
                project.name, workspace, project.gerrit_base_url
            )
            if err:
                project_errors[project.name] = err
                logger.warning("项目 %s: %s", project.name, err)
                continue
            for repo in repos:
                status = "pending" if repo.reachable else "unreachable"
                self._store.upsert_repo_meta(
                    repo.repo_key,
                    repo.project_name,
                    repo.repo_path,
                    repo.local_path,
                    repo.gerrit_base,
                    repo.gerrit_project,
                    status,
                )
                active_keys.add(repo.repo_key)
            all_repos.extend(repos)

        self._last_manifest_refresh = now
        self._store.remove_missing_repos(active_keys)
        with self._lock:
            self._repos = all_repos
        self.health.project_errors = project_errors

    def _check_repo(self, repo: DiscoveredRepo) -> None:
        row = self._store.get_repo_row(repo.repo_key)
        if row and row["next_retry_at"] and row["next_retry_at"] > time.time():
            return
        if not repo.reachable:
            self._store.upsert_repo_meta(
                repo.repo_key,
                repo.project_name,
                repo.repo_path,
                repo.local_path,
                repo.gerrit_base,
                repo.gerrit_project,
                "unreachable",
            )
            return

        repo_path = Path(repo.local_path)
        fail_count = int(row["fail_count"]) if row else 0
        try:
            git_fetch(repo_path, repo.remote_name)
            gerrit_base = enrich_gerrit_base(repo_path, repo.gerrit_base, repo.remote_name)
            if gerrit_base and gerrit_base != repo.gerrit_base:
                self._store.upsert_repo_meta(
                    repo.repo_key,
                    repo.project_name,
                    repo.repo_path,
                    repo.local_path,
                    gerrit_base,
                    repo.gerrit_project,
                    "ok",
                )
            old_hash = row["last_commit_hash"] if row else None
            commit_hash, commit_time, subject, author = read_head_commit(
                repo_path,
                remote=repo.remote_name,
                upstream=repo.upstream,
            )
            recent = read_recent_commits(repo_path, old_hash, commit_hash)
            changed = self._store.update_repo_success(
                repo.repo_key,
                commit_hash,
                commit_time,
                subject,
                author,
                recent,
            )
            if changed and old_hash is not None:
                self._notifier.on_repo_updated(repo.repo_key, commit_hash, recent)
        except GitError as exc:
            fail_count += 1
            delay = min(1800, 30 * (2 ** min(fail_count - 1, 6)))
            message = str(exc)
            logger.warning(
                "仓库 %s (%s) git 检查失败 [%d]: %s",
                repo.repo_key,
                repo.local_path,
                fail_count,
                message,
            )
            self._store.update_repo_failure(
                repo.repo_key,
                message,
                fail_count,
                time.time() + delay,
            )
        except Exception as exc:
            fail_count += 1
            delay = min(1800, 30 * (2 ** min(fail_count - 1, 6)))
            message = str(exc)
            logger.exception(
                "仓库 %s (%s) 检查异常 [%d]: %s",
                repo.repo_key,
                repo.local_path,
                fail_count,
                message,
            )
            self._store.update_repo_failure(
                repo.repo_key,
                message,
                fail_count,
                time.time() + delay,
            )
