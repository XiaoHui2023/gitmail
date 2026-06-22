from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from app_main.ai.prompts import COMMIT_UPDATE_SYSTEM_PROMPT, USER_MESSAGE_COMPLETENESS_FOOTER
from app_main.env_settings import AiSettings
from app_main.logging_setup import AI_CHAT_LOGGER_NAME
from app_main.models.repo import CommitInfo

logger = logging.getLogger(__name__)
chat_logger = logging.getLogger(AI_CHAT_LOGGER_NAME)

DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_SECONDS = 2.0
MAX_DIFF_CHARS = 32_000
MAX_USER_CHARS = 36_000
DEFAULT_MAX_TOKENS = 2048
INIT_TEST_SYSTEM_PROMPT = "你是连通性自检助手。只回复 OK，不要输出其它内容。"
INIT_TEST_USER_MESSAGE = "ping"
INIT_TEST_MAX_TOKENS = 16
INIT_TEST_TIMEOUT_SECONDS = 30


class AiSummaryError(RuntimeError):
    """AI 总结调用失败。"""


@dataclass(frozen=True)
class AiSummaryResult:
    text: str | None
    status: str


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n\n…（内容已截断）"


def chat_completions_url(settings: AiSettings) -> str:
    return settings.api_url.rstrip("/") + "/chat/completions"


def describe_ai_endpoint(settings: AiSettings) -> str:
    return f"url={chat_completions_url(settings)} model={settings.model}"


def build_user_message(
    project_name: str,
    repo_path: str,
    commits: list[CommitInfo],
    diff: str,
) -> str:
    lines = [
        f"项目: {project_name}",
        f"仓库: {repo_path}",
        "",
        "提交列表:",
    ]
    for commit in commits:
        lines.append(
            f"- {commit.hash[:12]} | {commit.author} | {commit.subject}"
        )
    lines.extend(["", "Diff:", _truncate(diff, MAX_DIFF_CHARS), "", USER_MESSAGE_COMPLETENESS_FOOTER.rstrip()])
    message = "\n".join(lines)
    return _truncate(message, MAX_USER_CHARS)


def _post_chat_completion(
    settings: AiSettings,
    *,
    system_prompt: str,
    user_message: str,
    timeout_seconds: float,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    url = chat_completions_url(settings)
    endpoint = describe_ai_endpoint(settings)
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        message = f"HTTP {exc.code}: {detail} ({endpoint})"
        logger.warning("AI 请求失败: %s", message)
        raise AiSummaryError(message) from exc
    except urllib.error.URLError as exc:
        message = f"{exc.reason} ({endpoint})"
        logger.warning("AI 请求失败: %s", message)
        raise AiSummaryError(message) from exc
    except TimeoutError as exc:
        message = f"请求超时 ({endpoint})"
        logger.warning("AI 请求失败: %s", message)
        raise AiSummaryError(message) from exc

    try:
        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        message = f"响应格式异常: {raw[:200]} ({endpoint})"
        logger.warning("AI 请求失败: %s", message)
        raise AiSummaryError(message) from exc

    text = str(content).strip()
    if not text:
        message = f"模型返回空内容 ({endpoint})"
        logger.warning("AI 请求失败: %s", message)
        raise AiSummaryError(message) from exc
    return text


def ping_ai_api(
    settings: AiSettings,
    *,
    timeout_seconds: float = INIT_TEST_TIMEOUT_SECONDS,
) -> None:
    """启动自检：调用一次最小对话，失败时抛出 AiSummaryError。"""
    _post_chat_completion(
        settings,
        system_prompt=INIT_TEST_SYSTEM_PROMPT,
        user_message=INIT_TEST_USER_MESSAGE,
        timeout_seconds=timeout_seconds,
        max_tokens=INIT_TEST_MAX_TOKENS,
    )


def _log_ai_exchange(
    *,
    settings: AiSettings,
    project_name: str,
    repo_path: str,
    system_prompt: str,
    user_message: str,
    response: str | None = None,
    error: str | None = None,
) -> None:
    chat_logger.info(
        "===== %s > %s (%s) =====",
        project_name,
        repo_path,
        describe_ai_endpoint(settings),
    )
    chat_logger.info("--- system ---\n%s", system_prompt)
    chat_logger.info("--- user ---\n%s", user_message)
    if response is not None:
        chat_logger.info("--- assistant ---\n%s", response)
    if error is not None:
        chat_logger.warning("--- error ---\n%s", error)


def summarize_repo_update(
    settings: AiSettings,
    *,
    project_name: str,
    repo_path: str,
    commits: list[CommitInfo],
    diff: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> AiSummaryResult:
    """调用 OpenAI 兼容接口生成更新总结；失败时返回 status=failed。"""
    if not settings.configured:
        return AiSummaryResult(text=None, status="skipped")

    user_message = build_user_message(project_name, repo_path, commits, diff)
    endpoint = describe_ai_endpoint(settings)
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            text = _post_chat_completion(
                settings,
                system_prompt=COMMIT_UPDATE_SYSTEM_PROMPT,
                user_message=user_message,
                timeout_seconds=timeout_seconds,
            )
            _log_ai_exchange(
                settings=settings,
                project_name=project_name,
                repo_path=repo_path,
                system_prompt=COMMIT_UPDATE_SYSTEM_PROMPT,
                user_message=user_message,
                response=text,
            )
            return AiSummaryResult(text=text, status="ready")
        except AiSummaryError as exc:
            last_error = exc
            _log_ai_exchange(
                settings=settings,
                project_name=project_name,
                repo_path=repo_path,
                system_prompt=COMMIT_UPDATE_SYSTEM_PROMPT,
                user_message=user_message,
                error=str(exc),
            )
            logger.warning(
                "AI 总结失败 (%s/%s) %s > %s (%s): %s",
                attempt + 1,
                max_retries,
                project_name,
                repo_path,
                endpoint,
                exc,
            )
        except Exception as exc:
            last_error = exc
            _log_ai_exchange(
                settings=settings,
                project_name=project_name,
                repo_path=repo_path,
                system_prompt=COMMIT_UPDATE_SYSTEM_PROMPT,
                user_message=user_message,
                error=str(exc),
            )
            logger.warning(
                "AI 总结异常 (%s/%s) %s > %s (%s): %s",
                attempt + 1,
                max_retries,
                project_name,
                repo_path,
                endpoint,
                exc,
            )
        if attempt + 1 < max_retries:
            delay = DEFAULT_RETRY_BASE_SECONDS * (2**attempt)
            time.sleep(delay)

    logger.warning(
        "AI 总结放弃 %s > %s (%s): %s",
        project_name,
        repo_path,
        endpoint,
        last_error,
    )
    return AiSummaryResult(text=None, status="failed")
