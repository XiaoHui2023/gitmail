from __future__ import annotations

from dataclasses import dataclass

from app_main.env_settings import AiSettings, SmtpSettings


@dataclass
class OperationalSmtp:
    """SMTP 运行时状态；启动自检失败时 enabled 为 False。"""

    settings: SmtpSettings
    enabled: bool = True
    init_error: str | None = None

    @property
    def configured(self) -> bool:
        return self.settings.configured and self.enabled

    @property
    def settings_filled(self) -> bool:
        return self.settings.configured

    def missing_fields(self) -> list[str]:
        return self.settings.missing_fields()

    def __getattr__(self, name: str) -> object:
        return getattr(self.settings, name)


@dataclass
class OperationalAi:
    """AI 运行时状态；启动自检失败时 enabled 为 False。"""

    settings: AiSettings
    enabled: bool = True
    init_error: str | None = None

    @property
    def configured(self) -> bool:
        return self.settings.configured and self.enabled

    @property
    def settings_filled(self) -> bool:
        return self.settings.configured

    def missing_fields(self) -> list[str]:
        return self.settings.missing_fields()

    def __getattr__(self, name: str) -> object:
        return getattr(self.settings, name)
