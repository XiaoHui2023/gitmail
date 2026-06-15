from __future__ import annotations

from pathlib import Path

import yaml

from app_main.models.config import AppConfig


def load_config(path: Path) -> AppConfig:
    """从 YAML 文件加载配置。

    Args:
        path: 配置文件路径。

    Returns:
        校验后的配置对象。
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw)


def resolve_config_path(explicit: str | None) -> Path:
    """解析配置文件路径，优先显式参数再回退默认名。"""
    if explicit:
        return Path(explicit).expanduser().resolve()
    for candidate in (Path("config.yaml"), Path("config.yml")):
        if candidate.is_file():
            return candidate.resolve()
    return Path("config.yaml").resolve()
