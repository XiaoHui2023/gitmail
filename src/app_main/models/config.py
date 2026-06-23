from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectConfig(BaseModel):
    """单个 repo 工作区监控项。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="展示用项目名")
    workspace: str = Field(description="含 .repo 的工作区根路径")
    gerrit_base_url: str | None = Field(
        default=None,
        description="Gerrit 根 URL（网页为 http），清单与远端均无法推断时使用",
    )


class AppConfig(BaseModel):
    """gitmail 主配置。"""

    model_config = ConfigDict(extra="ignore")

    email_domain: str = Field(description="用户邮箱后缀，如 corp.example.com")
    database_path: str = Field(
        default="",
        description="SQLite 数据库文件路径；留空则使用运行目录下 data/gitmail.db",
    )
    log_dir: str = Field(
        default="",
        description="日志根目录；留空则使用运行目录下 logs，按 年-月-日/时-分-秒/ 分文件存储",
    )
    listen_port: int = Field(default=0, description="监听端口；0 表示由系统分配空闲端口")
    public_base_path: str = Field(default="", description="对外 URL 路径前缀，如 /tools/gitmail")
    allow_anonymous_repo_list: bool = Field(default=True, description="未在白名单时是否允许只读查看全部仓库")
    poll_interval_seconds: int = Field(default=120, description="全局仓库轮询间隔（秒）")
    manifest_refresh_seconds: int = Field(default=300, description="清单重读间隔（秒）")
    fetch_concurrency: int = Field(default=4, description="并行 git 操作上限；机器卡顿时可再调低")
    remote_probe_before_fetch: bool = Field(
        default=True,
        description="无本地变更时先 ls-remote 探测远端；未变则跳过 fetch",
    )
    frontend_poll_seconds: int = Field(default=30, description="建议前端列表刷新间隔（秒）")
    smtp_startup_check: bool = Field(
        default=True,
        description="启动时向 SMTP 账号发送自检邮件；false 则跳过",
    )
    ai_startup_check: bool = Field(
        default=True,
        description="启动时调用一次最小 AI 对话验证连通性；false 则跳过",
    )
    trusted_proxy_header: str = Field(default="", description="可信代理 IP 头名，如 X-Forwarded-For")
    ip_whitelist: list[str] = Field(default_factory=lambda: ["127.0.0.1"], description="允许写操作的 IP 模式")
    ip_user_map: dict[str, str] = Field(default_factory=dict, description="IP 到用户名的显式映射")
    username_extract_regexes: list[str] = Field(
        default_factory=list,
        description="从解析到的用户名中提取真实邮箱前缀的正则表达式列表",
    )
    projects: list[ProjectConfig] = Field(default_factory=list, description="待监控项目列表")

    @field_validator("username_extract_regexes")
    @classmethod
    def validate_username_extract_regexes(cls, value: list[str]) -> list[str]:
        for pattern in value:
            re.compile(pattern)
        return value
