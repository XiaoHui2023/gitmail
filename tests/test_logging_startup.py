from __future__ import annotations

import logging
import re
from pathlib import Path

from app_main.env_settings import AiSettings, SmtpSettings
from app_main.feature_runtime import OperationalAi, OperationalSmtp
from app_main.logging_setup import AI_CHAT_LOGGER_NAME, setup_logging
from app_main.models.config import AppConfig
from app_main.paths import create_log_session_dir, resolve_log_root
from app_main.startup_display import build_ai_status, build_feature_statuses, build_smtp_status


def test_resolve_log_root_default(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = resolve_log_root("")
    assert root == (tmp_path / "logs").resolve()
    assert root.is_dir()


def test_create_log_session_dir_layout(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    session = create_log_session_dir("run-logs")
    assert session.parent.parent == (tmp_path / "run-logs").resolve()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", session.parent.name)
    assert re.fullmatch(r"\d{2}-\d{2}-\d{2}", session.name)
    assert session.is_dir()


def test_setup_logging_writes_split_files(tmp_path) -> None:
    session = tmp_path / "2026-06-22" / "12-00-00"
    session.mkdir(parents=True)
    setup_logging(session)

    logging.getLogger("app_main.test").info("app message")
    logging.getLogger("app_main.test").warning("warn message")
    logging.getLogger(AI_CHAT_LOGGER_NAME).info("ai chat")

    assert (session / "app.log").read_text(encoding="utf-8").count("app message") == 1
    assert "ai chat" not in (session / "app.log").read_text(encoding="utf-8")
    assert (session / "error.log").read_text(encoding="utf-8").count("warn message") == 1
    assert (session / "ai.log").read_text(encoding="utf-8").count("ai chat") == 1


def test_build_smtp_status_configured() -> None:
    smtp = OperationalSmtp(
        SmtpSettings(
            SMTP_HOST="smtp.test",
            SMTP_USER="u@test",
            SMTP_PASSWORD="secret",
            SMTP_FROM="Git <u@test>",
        )
    )
    status = build_smtp_status(smtp)
    assert status.enabled
    assert "smtp.test" in status.detail


def test_build_smtp_status_missing() -> None:
    status = build_smtp_status(OperationalSmtp(SmtpSettings()))
    assert not status.enabled
    assert "SMTP_HOST" in status.hint


def test_build_ai_status_missing() -> None:
    status = build_ai_status(OperationalAi(AiSettings()))
    assert not status.enabled
    assert "AI_API_URL" in status.hint


def test_build_feature_statuses_includes_log_session(tmp_path) -> None:
    config = AppConfig(email_domain="corp.test", projects=[])
    session = tmp_path / "session"
    session.mkdir()
    items = build_feature_statuses(
        config,
        OperationalSmtp(SmtpSettings()),
        OperationalAi(AiSettings()),
        config_path=tmp_path / "config.yaml",
        config_found=True,
        log_session_dir=session,
    )
    names = [item.name for item in items]
    assert "邮件通知" in names
    assert "AI 总结" in names
    assert "日志" in names
