from __future__ import annotations

from unittest.mock import patch

import pytest

from app_main.env_settings import AiSettings, SmtpSettings
from app_main.feature_runtime import OperationalAi, OperationalSmtp
from app_main.startup_checks import run_startup_checks
from app_main.startup_display import build_ai_status, build_smtp_status


def test_startup_checks_smtp_failure_disables_feature() -> None:
    smtp = OperationalSmtp(
        SmtpSettings(
            SMTP_HOST="smtp.test",
            SMTP_USER="u@test.com",
            SMTP_PASSWORD="secret",
        )
    )
    ai = OperationalAi(AiSettings())

    with patch(
        "app_main.startup_checks.send_startup_test_email",
        side_effect=RuntimeError("auth failed"),
    ):
        run_startup_checks(smtp, ai)

    assert not smtp.enabled
    assert smtp.init_error == "auth failed"
    assert not smtp.configured


def test_startup_checks_ai_failure_disables_feature() -> None:
    smtp = OperationalSmtp(SmtpSettings())
    ai = OperationalAi(
        AiSettings(
            AI_API_URL="https://example.com/v1",
            AI_API_KEY="key",
            AI_MODEL="m",
        )
    )

    with patch(
        "app_main.startup_checks.ping_ai_api",
        side_effect=RuntimeError("timeout"),
    ):
        run_startup_checks(smtp, ai)

    assert not ai.enabled
    assert ai.init_error == "timeout"
    assert not ai.configured


def test_startup_checks_skips_when_not_configured() -> None:
    smtp = OperationalSmtp(SmtpSettings())
    ai = OperationalAi(AiSettings())

    with patch("app_main.startup_checks.send_startup_test_email") as send_mock, patch(
        "app_main.startup_checks.ping_ai_api"
    ) as ai_mock:
        run_startup_checks(smtp, ai)

    send_mock.assert_not_called()
    ai_mock.assert_not_called()
    assert smtp.enabled
    assert ai.enabled


def test_startup_checks_skips_when_disabled() -> None:
    smtp = OperationalSmtp(
        SmtpSettings(
            SMTP_HOST="smtp.test",
            SMTP_USER="u@test.com",
            SMTP_PASSWORD="secret",
        ),
        startup_check=False,
    )
    ai = OperationalAi(
        AiSettings(
            AI_API_URL="https://example.com/v1",
            AI_API_KEY="key",
            AI_MODEL="m",
        ),
        startup_check=False,
    )

    with patch("app_main.startup_checks.send_startup_test_email") as send_mock, patch(
        "app_main.startup_checks.ping_ai_api"
    ) as ai_mock:
        run_startup_checks(smtp, ai)

    send_mock.assert_not_called()
    ai_mock.assert_not_called()
    assert smtp.enabled
    assert ai.enabled
    assert smtp.configured
    assert ai.configured


def test_build_smtp_status_shows_init_failure() -> None:
    smtp = OperationalSmtp(
        SmtpSettings(
            SMTP_HOST="smtp.test",
            SMTP_USER="u@test.com",
            SMTP_PASSWORD="secret",
        ),
        enabled=False,
        init_error="connection refused",
    )
    status = build_smtp_status(smtp)
    assert not status.enabled
    assert status.status_style == "status.warn"
    assert "connection refused" in status.hint


def test_build_ai_status_shows_init_failure() -> None:
    ai = OperationalAi(
        AiSettings(
            AI_API_URL="https://example.com/v1",
            AI_API_KEY="key",
            AI_MODEL="m",
        ),
        enabled=False,
        init_error="HTTP 401",
    )
    status = build_ai_status(ai)
    assert not status.enabled
    assert "HTTP 401" in status.hint


def test_build_ai_status_shows_startup_check_disabled() -> None:
    ai = OperationalAi(
        AiSettings(
            AI_API_URL="https://example.com/v1",
            AI_API_KEY="key",
            AI_MODEL="m",
        ),
        startup_check=False,
    )
    status = build_ai_status(ai)
    assert status.enabled
    assert "ai_startup_check=false" in status.hint


def test_operational_smtp_delegates_settings_fields() -> None:
    smtp = OperationalSmtp(
        SmtpSettings(
            SMTP_HOST="smtp.test",
            SMTP_USER="u@test.com",
            SMTP_PASSWORD="secret",
            SMTP_PORT=465,
        )
    )
    assert smtp.smtp_host == "smtp.test"
    assert smtp.smtp_port == 465
