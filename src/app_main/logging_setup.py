from __future__ import annotations

import logging
from pathlib import Path

AI_CHAT_LOGGER_NAME = "app_main.ai.chat"

_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
_FILE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_session_dir: Path | None = None


class _ExcludeLoggerFilter(logging.Filter):
    def __init__(self, logger_name: str) -> None:
        super().__init__()
        self._logger_name = logger_name

    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith(self._logger_name)


def get_log_session_dir() -> Path | None:
    return _session_dir


def setup_logging(session_dir: Path | None, *, console_level: int = logging.WARNING) -> None:
    """配置分文件日志；控制台仅输出警告及以上。"""
    global _session_dir
    _session_dir = session_dir

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
    root.addHandler(console)

    if session_dir is not None:
        app_handler = logging.FileHandler(session_dir / "app.log", encoding="utf-8")
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_LOG_DATEFMT))
        app_handler.addFilter(_ExcludeLoggerFilter(AI_CHAT_LOGGER_NAME))
        root.addHandler(app_handler)

        error_handler = logging.FileHandler(session_dir / "error.log", encoding="utf-8")
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_LOG_DATEFMT))
        root.addHandler(error_handler)

    ai_logger = logging.getLogger(AI_CHAT_LOGGER_NAME)
    ai_logger.handlers.clear()
    ai_logger.propagate = False
    ai_logger.setLevel(logging.DEBUG)
    if session_dir is not None:
        ai_handler = logging.FileHandler(session_dir / "ai.log", encoding="utf-8")
        ai_handler.setLevel(logging.DEBUG)
        ai_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_LOG_DATEFMT))
        ai_logger.addHandler(ai_handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
