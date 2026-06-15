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

    @property
    def configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)
