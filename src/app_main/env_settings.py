from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SmtpSettings(BaseSettings):
    """管理员 SMTP 参数，来自 .env。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    startup_check: bool = Field(default=True, alias="SMTP_STARTUP_CHECK")

    @property
    def configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.smtp_host.strip():
            missing.append("SMTP_HOST")
        if not self.smtp_user.strip():
            missing.append("SMTP_USER")
        if not self.smtp_password.strip():
            missing.append("SMTP_PASSWORD")
        return missing


class AiSettings(BaseSettings):
    """OpenAI 兼容 AI 接口参数，来自 .env。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_url: str = Field(default="", alias="AI_API_URL")
    api_key: str = Field(default="", alias="AI_API_KEY")
    model: str = Field(default="", alias="AI_MODEL")
    startup_check: bool = Field(default=True, alias="AI_STARTUP_CHECK")

    @property
    def configured(self) -> bool:
        return bool(self.api_url and self.api_key and self.model)

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.api_url.strip():
            missing.append("AI_API_URL")
        if not self.api_key.strip():
            missing.append("AI_API_KEY")
        if not self.model.strip():
            missing.append("AI_MODEL")
        return missing
