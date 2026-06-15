from __future__ import annotations

import logging

from app_main.env_settings import SmtpSettings
from app_main.mail.sender import send_repo_update_email
from app_main.models.config import AppConfig
from app_main.models.repo import CommitInfo
from app_main.store.database import Store

logger = logging.getLogger(__name__)


class Notifier:
    """仓库更新后的邮件通知。"""

    def __init__(self, store: Store, config: AppConfig, smtp: SmtpSettings) -> None:
        self._store = store
        self._config = config
        self._smtp = smtp

    def on_repo_updated(
        self,
        repo_key: str,
        commit_hash: str,
        recent_commits: list[CommitInfo],
    ) -> None:
        if self._store.is_notified(repo_key, commit_hash):
            return
        row = self._store.get_repo_row(repo_key)
        if row is None:
            return
        snapshot = self._store.row_to_snapshot(row)
        subscribers = self._store.list_subscribers(repo_key)
        if not subscribers:
            self._store.mark_notified(repo_key, commit_hash)
            return
        for username in subscribers:
            if username == "unknown":
                continue
            if not self._store.get_email_enabled(username):
                continue
            to_addr = f"{username}@{self._config.email_domain}"
            try:
                send_repo_update_email(self._smtp, to_addr, snapshot, recent_commits)
            except Exception as exc:
                logger.warning("邮件发送失败 %s %s: %s", username, repo_key, exc)
        self._store.mark_notified(repo_key, commit_hash)
