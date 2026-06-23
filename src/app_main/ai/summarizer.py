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
_RESPONSE_PREVIEW_CHARS = 500


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


def _response_preview(raw: str, limit: int = _RESPONSE_PREVIEW_CHARS) -> str:
    if len(raw) <= limit:
        return raw
    return raw[: limit - 12] + "…（已截断）"


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


def _parse_chat_completion_content(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AiSummaryError(
            "响应 JSON 解析失败: "
            f"{exc.msg}（字符位置 {exc.pos}）; "
            f"响应片段: {_response_preview(raw)!r}"
        ) from exc

    if not isinstance(data, dict):
        raise AiSummaryError(
            "响应根节点应为 JSON object，"
            f"实际为 {type(data).__name__}; "
            f"响应片段: {_response_preview(raw)!r}"
        )

    if "error" in data:
        error = data["error"]
        if isinstance(error, dict):
            detail = error.get("message") or error.get("type") or json.dumps(error, ensure_ascii=False)
        else:
            detail = str(error)
        raise AiSummaryError(f"接口返回 error 字段: {detail}; 响应片段: {_response_preview(raw)!r}")

    choices = data.get("choices")
    if choices is None:
        keys = ", ".join(sorted(data)) or "（空）"
        raise AiSummaryError(
            f"响应缺少 choices 字段; 顶层字段: {keys}; "
            f"响应片段: {_response_preview(raw)!r}"
        )
    if not isinstance(choices, list):
        raise AiSummaryError(
            f"choices 应为数组，实际为 {type(choices).__name__}; "
            f"响应片段: {_response_preview(raw)!r}"
        )
    if not choices:
        raise AiSummaryError(f"choices 数组为空; 响应片段: {_response_preview(raw)!r}")

    first = choices[0]
    if not isinstance(first, dict):
        raise AiSummaryError(
            f"choices[0] 应为 object，实际为 {type(first).__name__}; "
            f"响应片段: {_response_preview(raw)!r}"
        )

    message = first.get("message")
    if not isinstance(message, dict):
        keys = ", ".join(sorted(first)) or "（空）"
        raise AiSummaryError(
            f"choices[0] 缺少 message 对象; choices[0] 字段: {keys}; "
            f"响应片段: {_response_preview(raw)!r}"
        )

    if "content" not in message:
        keys = ", ".join(sorted(message)) or "（空）"
        raise AiSummaryError(
            f"message 缺少 content 字段; message 字段: {keys}; "
            f"响应片段: {_response_preview(raw)!r}"
        )

    content = message["content"]
    if content is None:
        raise AiSummaryError(f"message.content 为 null; 响应片段: {_response_preview(raw)!r}")

    text = str(content).strip()
    if not text:
        raise AiSummaryError(f"模型返回空内容; 响应片段: {_response_preview(raw)!r}")
    return text


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
        return _parse_chat_completion_content(raw)
    except AiSummaryError as exc:
        message = f"{exc} ({endpoint})"
        logger.warning("AI 请求失败: %s", message)
        raise AiSummaryError(message) from exc


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


def _log_ai_response(
    *,
    project_name: str,
    repo_path: str,
    response: str,
) -> None:
    chat_logger.info("[%s > %s]\n%s", project_name, repo_path, response)


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
            _log_ai_response(
                project_name=project_name,
                repo_path=repo_path,
                response=text,
            )
            return AiSummaryResult(text=text, status="ready")
        except AiSummaryError as exc:
            last_error = exc
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
