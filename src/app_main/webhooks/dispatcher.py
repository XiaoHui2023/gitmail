from __future__ import annotations

import logging
import secrets
import threading
import uuid

from app_main.manifest.gerrit_urls import build_gerrit_urls
from app_main.models.repo import CommitInfo
from app_main.store.database import Store
from app_main.webhooks.client import DeliveryResult, deliver_webhook
from app_main.webhooks.payload import build_test_payload, build_update_payload

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """仓库更新 Webhook 投递。"""

    def __init__(self, store: Store) -> None:
        self._store = store

    @staticmethod
    def generate_secret() -> str:
        return f"whsec_{secrets.token_urlsafe(24)}"

    def on_repo_updated(
        self,
        repo_key: str,
        project_name: str,
        repo_path: str,
        old_hash: str,
        old_subject: str | None,
        commit_hash: str,
        commit_time: int,
        subject: str,
        author: str,
        recent: list[CommitInfo],
        *,
        gerrit_base: str | None,
        gerrit_project: str | None,
        gerrit_change_number: int | None,
    ) -> None:
        hooks = self._store.list_enabled_webhooks_for_repo(repo_key)
        if not hooks:
            return

        def task() -> None:
            gerrit_links = self._gerrit_links(
                gerrit_base, gerrit_project, commit_hash, gerrit_change_number
            )
            for hook in hooks:
                if self._store.is_webhook_delivered(hook["id"], commit_hash):
                    continue
                payload = build_update_payload(
                    event_id=f"evt_{uuid.uuid4().hex}",
                    repo_key=repo_key,
                    project_name=project_name,
                    repo_path=repo_path,
                    old_hash=old_hash,
                    old_subject=old_subject,
                    commit_hash=commit_hash,
                    commit_time=commit_time,
                    subject=subject,
                    author=author,
                    recent=recent,
                    **gerrit_links,
                )
                result = deliver_webhook(
                    hook["url"],
                    hook["secret"],
                    "repository.commit.updated",
                    payload,
                )
                self._store.mark_webhook_delivered(hook["id"], commit_hash)
                self._store.update_webhook_delivery_status(
                    hook["id"],
                    result.ok,
                    result.status_code,
                    result.error,
                )
                if result.ok:
                    logger.info("Webhook 投递成功 %s -> %s", hook["id"], hook["url"])
                else:
                    logger.warning(
                        "Webhook 投递失败 %s -> %s: %s",
                        hook["id"],
                        hook["url"],
                        result.error,
                    )

        threading.Thread(
            target=task,
            name=f"gitmail-webhook-{repo_key}",
            daemon=True,
        ).start()

    def send_test(self, hook: dict) -> DeliveryResult:
        repo_row = self._store.get_repo_row(hook["repo_key"])
        project_name = repo_row["project_name"] if repo_row else hook["repo_key"].split("::", 1)[0]
        repo_path = repo_row["repo_path"] if repo_row else hook["repo_key"].split("::", 1)[-1]
        payload = build_test_payload(
            hook["id"],
            hook["repo_key"],
            project_name,
            repo_path,
        )
        result = deliver_webhook(
            hook["url"],
            hook["secret"],
            "webhook.test",
            payload,
        )
        self._store.update_webhook_delivery_status(
            hook["id"],
            result.ok,
            result.status_code,
            result.error,
        )
        return result

    @staticmethod
    def _gerrit_links(
        gerrit_base: str | None,
        gerrit_project: str | None,
        commit_hash: str,
        change_number: int | None,
    ) -> dict:
        urls = build_gerrit_urls(gerrit_base, gerrit_project, commit_hash, change_number)
        return {
            "gerrit_project_url": urls.project_url,
            "gerrit_commit_url": urls.commit_url,
            "gerrit_change_number": change_number,
        }
