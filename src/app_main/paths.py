from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys


def resolve_data_dir() -> Path:
    """运行期数据目录（SQLite 等）。"""
    if getattr(sys, "frozen", False):
        return Path.cwd() / "data"
    return Path(__file__).resolve().parents[2] / "data"


def resolve_database_path(database_path: str) -> Path:
    """解析 SQLite 数据库文件路径。

    Args:
        database_path: 配置项；空字符串时使用默认 data/gitmail.db。

    Returns:
        绝对路径。
    """
    trimmed = database_path.strip()
    if not trimmed:
        return resolve_data_dir() / "gitmail.db"
    path = Path(trimmed).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def resolve_log_root(log_dir: str) -> Path:
    """解析日志根目录。

    Args:
        log_dir: 配置项；空字符串时使用运行目录下 logs。

    Returns:
        绝对路径。
    """
    trimmed = log_dir.strip()
    if not trimmed:
        path = Path.cwd() / "logs"
    else:
        path = Path(trimmed).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def create_log_session_dir(log_dir: str) -> Path:
    """创建本次启动的日志会话目录：{log_root}/{年-月-日}/{时-分-秒}/。"""
    root = resolve_log_root(log_dir)
    now = datetime.now()
    session = root / now.strftime("%Y-%m-%d") / now.strftime("%H-%M-%S")
    session.mkdir(parents=True, exist_ok=True)
    return session.resolve()


def resolve_frontend_dist() -> Path:
    """定位 Vite 构建产物目录，兼容开发与 PyInstaller 打包。"""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return base / "frontend" / "dist"
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"
