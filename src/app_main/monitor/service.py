from __future__ import annotations

import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from app_main.ai.summarizer import AiSummaryResult, summarize_repo_update
from app_main.env_settings import AiSettings
from app_main.git.commands import (
    GitError,
    UpstreamRefError,
    enrich_gerrit_base,
    git_fetch,
    probe_remote_unchanged,
    read_commit_diff,
    read_head_commit,
    read_recent_commits,
)
from app_main.mail.notifier import Notifier
from app_main.manifest.gerrit_urls import resolve_gerrit_change_number
from app_main.manifest.parser import discover_project_repos
from app_main.models.config import AppConfig
from app_main.models.repo import DiscoveredRepo
from app_main.store.database import Store
from app_main.webhooks.dispatcher import WebhookDispatcher

logger = logging.getLogger(__name__)

MONITOR_START_TIMEOUT_SECONDS = 5.0


class MonitorNotRunningError(RuntimeError):
    """监控后台线程未在预期时间内进入运行状态。"""


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

    def __init__(
        self,
        config: AppConfig,
        store: Store,
        notifier: Notifier,
        ai: AiSettings | None = None,
        webhooks: WebhookDispatcher | None = None,
    ) -> None:
        self._config = config
        self._store = store
        self._notifier = notifier
        self._webhooks = webhooks or WebhookDispatcher(store)
        self._ai = ai or AiSettings()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._repos: list[DiscoveredRepo] = []
        self._manifest_mtime: dict[str, float] = {}
        self._last_manifest_refresh = 0.0
        self.health = MonitorHealth()
        self._lock = threading.Lock()
        self._executor: ThreadPoolExecutor | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="gitmail-monitor", daemon=True)
        self._thread.start()

    def is_running(self) -> bool:
        thread = self._thread
        return self.health.running and thread is not None and thread.is_alive()

    def ensure_running(self, timeout: float = MONITOR_START_TIMEOUT_SECONDS) -> None:
        """等待监控线程进入运行状态；超时或线程退出时抛出 MonitorNotRunningError。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            thread = self._thread
            if thread is not None and not thread.is_alive():
                raise MonitorNotRunningError("监控线程已退出")
            if self.health.running:
                return
            time.sleep(0.05)
        raise MonitorNotRunningError(
            f"监控调度在 {timeout:.0f}s 内未进入运行状态"
        )

    def stop(self) -> None:
        self._stop.set()
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None
        if self._thread:
            self._thread.join(timeout=5)

    def _get_executor(self) -> ThreadPoolExecutor:
        workers = max(1, self._config.fetch_concurrency)
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix="gitmail-fetch",
            )
        return self._executor

    def _next_poll_at(self, repo_key: str, last_commit_time: int | None = None) -> float:
        interval = max(30, self._config.poll_interval_seconds)
        if last_commit_time:
            age_days = max(0.0, (time.time() - last_commit_time) / 86400)
            if age_days > 365:
                interval = int(interval * 8)
            elif age_days > 180:
                interval = int(interval * 4)
            elif age_days > 90:
                interval = int(interval * 2)
            elif age_days > 30:
                interval = int(interval * 1.5)
        slot = (hash(repo_key) & 0x7FFFFFFF) % interval
        return time.time() + interval + slot * 0.2 + random.uniform(0, 3)

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
            logger.info(
                "监控轮次完成: 仓库 %d 个, 耗时 %.1fs, 失败 %d 个",
                self.health.last_round_repo_count,
                self.health.last_round_seconds,
                self.health.failed_repo_count,
            )
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
        pool = self._get_executor()
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
        refreshed_projects: set[str] = set()

        for project in self._config.projects:
            workspace = Path(project.workspace).expanduser()
            repos, err = discover_project_repos(
                project.name, workspace, project.gerrit_base_url
            )
            if err:
                project_errors[project.name] = err
                logger.warning("项目 %s: %s", project.name, err)
                continue
            refreshed_projects.add(project.name)
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
        self._store.remove_missing_repos(active_keys, refreshed_projects)
        with self._lock:
            self._repos = all_repos
        self.health.project_errors = project_errors

    def _check_repo(self, repo: DiscoveredRepo) -> None:
        row = self._store.get_repo_row(repo.repo_key)
        now = time.time()
        if row:
            if row["next_retry_at"] and row["next_retry_at"] > now:
                return
            if row["status"] == "ok" and row["next_poll_at"] and row["next_poll_at"] > now:
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
        upstream_ref_index = int(row["upstream_ref_index"]) if row else 0
        gerrit_change_query_index = int(row["gerrit_change_query_index"]) if row else 0
        gerrit_change_lookup_hash = row["gerrit_change_lookup_hash"] if row else None
        old_hash = row["last_commit_hash"] if row else None
        try:
            if (
                self._config.remote_probe_before_fetch
                and old_hash
                and row
                and row["status"] == "ok"
            ):
                unchanged = probe_remote_unchanged(
                    repo_path,
                    remote=repo.remote_name,
                    upstream=repo.upstream,
                    start_index=upstream_ref_index,
                    known_hash=old_hash,
                )
                if unchanged is True:
                    commit_time = int(row["last_commit_time"]) if row["last_commit_time"] else None
                    self._store.defer_repo_poll(
                        repo.repo_key,
                        self._next_poll_at(repo.repo_key, commit_time),
                    )
                    return

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
            try:
                commit_hash, commit_time, subject, author, upstream_ref_index = read_head_commit(
                    repo_path,
                    remote=repo.remote_name,
                    upstream=repo.upstream,
                    start_index=upstream_ref_index,
                )
            except UpstreamRefError:
                self._store.reset_upstream_ref_index(repo.repo_key)
                raise
            recent = read_recent_commits(repo_path, old_hash, commit_hash)
            existing_change_number = row["gerrit_change_number"] if row else None
            gerrit_change_number = existing_change_number
            need_change_lookup = gerrit_base and (
                commit_hash != old_hash or not existing_change_number
            )
            if need_change_lookup and gerrit_change_lookup_hash != commit_hash:
                try:
                    gerrit_change_number, gerrit_change_query_index = resolve_gerrit_change_number(
                        gerrit_base,
                        repo.gerrit_project,
                        commit_hash,
                        start_index=gerrit_change_query_index,
                    )
                    gerrit_change_lookup_hash = commit_hash
                    if gerrit_change_number is None:
                        logger.warning(
                            "Gerrit change number 未找到 %s (%s)",
                            repo.repo_key,
                            commit_hash,
                        )
                except Exception as exc:
                    gerrit_change_lookup_hash = commit_hash
                    logger.warning(
                        "Gerrit change number 查询失败 %s (%s): %s",
                        repo.repo_key,
                        commit_hash,
                        exc,
                    )
                    if commit_hash != old_hash:
                        gerrit_change_number = None
            changed = self._store.update_repo_success(
                repo.repo_key,
                commit_hash,
                commit_time,
                subject,
                author,
                recent,
                gerrit_change_number,
                upstream_ref_index,
                gerrit_change_query_index,
                gerrit_change_lookup_hash,
                self._next_poll_at(repo.repo_key, commit_time),
            )
            if changed and old_hash is not None:
                old_subject = row["last_commit_subject"] if row else None
                self._webhooks.on_repo_updated(
                    repo.repo_key,
                    repo.project_name,
                    repo.repo_path,
                    old_hash,
                    old_subject,
                    commit_hash,
                    commit_time,
                    subject,
                    author,
                    recent,
                    gerrit_base=gerrit_base,
                    gerrit_project=repo.gerrit_project,
                    gerrit_change_number=gerrit_change_number,
                )
                self._schedule_ai_summary(repo, old_hash, commit_hash, recent)
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

    def _schedule_ai_summary(
        self,
        repo: DiscoveredRepo,
        old_hash: str,
        commit_hash: str,
        recent: list,
    ) -> None:
        def task() -> None:
            try:
                result = self._run_ai_summary(repo, old_hash, commit_hash, recent)
                if not self._store.update_ai_summary(
                    repo.repo_key,
                    commit_hash,
                    result.text,
                    result.status,
                ):
                    return
                self._notifier.on_repo_updated(
                    repo.repo_key,
                    commit_hash,
                    recent,
                    result.text,
                )
            except Exception as exc:
                logger.exception(
                    "AI 总结后台任务异常 %s: %s",
                    repo.repo_key,
                    exc,
                )
                if self._store.update_ai_summary(
                    repo.repo_key, commit_hash, None, "failed"
                ):
                    self._notifier.on_repo_updated(
                        repo.repo_key, commit_hash, recent, None
                    )

        threading.Thread(
            target=task,
            name=f"gitmail-ai-{repo.repo_key}",
            daemon=True,
        ).start()

    def _run_ai_summary(
        self,
        repo: DiscoveredRepo,
        old_hash: str,
        commit_hash: str,
        recent: list,
    ):
        if not self._ai.configured:
            return AiSummaryResult(text=None, status="skipped")

        repo_path = Path(repo.local_path)
        diff = read_commit_diff(repo_path, old_hash, commit_hash)
        return summarize_repo_update(
            self._ai,
            project_name=repo.project_name,
            repo_path=repo.repo_path,
            commits=recent,
            diff=diff,
        )
