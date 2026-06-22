from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app_main.ai.summarizer import (
    AiSummaryError,
    build_user_message,
    ping_ai_api,
    summarize_repo_update,
)
from app_main.env_settings import AiSettings
from app_main.feature_runtime import OperationalAi
from app_main.models.repo import CommitInfo


def test_build_user_message_includes_commits_and_diff() -> None:
    commits = [
        CommitInfo(
            hash="abc123def456",
            author="alice",
            committed_at=1,
            subject="fix login",
        )
    ]
    text = build_user_message("proj", "a/b", commits, "diff content")
    assert "proj" in text
    assert "a/b" in text
    assert "alice" in text
    assert "fix login" in text
    assert "diff content" in text
    assert "全部关键变更" in text


def test_system_prompt_requires_completeness() -> None:
    from app_main.ai.prompts import COMMIT_UPDATE_SYSTEM_PROMPT

    assert "不得遗漏" in COMMIT_UPDATE_SYSTEM_PROMPT
    assert "自检" in COMMIT_UPDATE_SYSTEM_PROMPT


def test_summarize_skipped_when_not_configured() -> None:
    ai = AiSettings()
    result = summarize_repo_update(
        ai,
        project_name="p",
        repo_path="r",
        commits=[],
        diff="",
    )
    assert result.status == "skipped"
    assert result.text is None


def test_summarize_success() -> None:
    ai = AiSettings(
        AI_API_URL="https://example.com/v1",
        AI_API_KEY="key",
        AI_MODEL="test-model",
    )
    payload = {
        "choices": [{"message": {"content": "  更新了登录逻辑。  "}}],
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(payload).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("app_main.ai.summarizer.urllib.request.urlopen", return_value=mock_response):
        result = summarize_repo_update(
            ai,
            project_name="p",
            repo_path="r",
            commits=[],
            diff="",
            max_retries=1,
        )
    assert result.status == "ready"
    assert result.text == "更新了登录逻辑。"


def test_summarize_retries_then_fails() -> None:
    ai = AiSettings(
        AI_API_URL="https://example.com/v1",
        AI_API_KEY="key",
        AI_MODEL="test-model",
    )

    with patch(
        "app_main.ai.summarizer._post_chat_completion",
        side_effect=AiSummaryError("boom"),
    ), patch("app_main.ai.summarizer.time.sleep"):
        result = summarize_repo_update(
            ai,
            project_name="p",
            repo_path="r",
            commits=[],
            diff="",
            max_retries=2,
        )
    assert result.status == "failed"
    assert result.text is None


def test_test_ai_connection_calls_api() -> None:
    ai = AiSettings(
        AI_API_URL="https://example.com/v1",
        AI_API_KEY="key",
        AI_MODEL="test-model",
    )
    with patch(
        "app_main.ai.summarizer._post_chat_completion",
        return_value="OK",
    ) as mock_post:
        ping_ai_api(ai)
    mock_post.assert_called_once()


def test_summarize_skipped_when_operational_disabled() -> None:
    ai = OperationalAi(
        AiSettings(
            AI_API_URL="https://example.com/v1",
            AI_API_KEY="key",
            AI_MODEL="test-model",
        ),
        enabled=False,
        init_error="init failed",
    )
    result = summarize_repo_update(
        ai,
        project_name="p",
        repo_path="r",
        commits=[],
        diff="",
    )
    assert result.status == "skipped"
