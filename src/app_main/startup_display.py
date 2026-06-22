from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from app_main.feature_runtime import OperationalAi, OperationalSmtp
from app_main.models.config import AppConfig
from app_main.paths import resolve_database_path, resolve_log_root
from app_main.terminal_theme import make_console


@dataclass(frozen=True)
class FeatureStatus:
    name: str
    enabled: bool
    detail: str
    hint: str = ""
    status_style: str = ""


def build_smtp_status(smtp: OperationalSmtp) -> FeatureStatus:
    missing = smtp.missing_fields()
    if missing:
        return FeatureStatus(
            "邮件通知",
            False,
            "未配置",
            f"在 .env 中填写：{', '.join(missing)}",
        )
    if not smtp.enabled:
        return FeatureStatus(
            "邮件通知",
            False,
            "初始化自检失败，已关闭",
            smtp.init_error or "未知错误",
            status_style="status.warn",
        )
    detail = f"{smtp.smtp_host}:{smtp.smtp_port}"
    if smtp.smtp_from:
        detail += f" · 发件人 {smtp.smtp_from}"
    else:
        detail += f" · 发件人 {smtp.smtp_user}"
    if smtp.startup_check:
        hint = f"已向 {smtp.smtp_user} 发送自检邮件"
    else:
        hint = "启动自检已关闭（config.yaml smtp_startup_check=false）"
    return FeatureStatus(
        "邮件通知",
        True,
        detail,
        hint,
    )


def build_ai_status(ai: OperationalAi) -> FeatureStatus:
    missing = ai.missing_fields()
    if missing:
        return FeatureStatus(
            "AI 总结",
            False,
            "未配置",
            f"在 .env 中填写：{', '.join(missing)}",
        )
    if not ai.enabled:
        return FeatureStatus(
            "AI 总结",
            False,
            "初始化自检失败，已关闭",
            ai.init_error or "未知错误",
            status_style="status.warn",
        )
    hint = (
        "接口连通性自检通过"
        if ai.startup_check
        else "启动自检已关闭（config.yaml ai_startup_check=false）"
    )
    return FeatureStatus(
        "AI 总结",
        True,
        f"{ai.model} @ {ai.api_url}",
        hint,
    )


def build_feature_statuses(
    config: AppConfig,
    smtp: OperationalSmtp,
    ai: OperationalAi,
    *,
    config_path: Path,
    config_found: bool,
    log_session_dir: Path | None,
) -> list[FeatureStatus]:
    items = [
        FeatureStatus(
            "配置文件",
            config_found,
            str(config_path.resolve()) if config_found else str(config_path),
            "" if config_found else "使用空配置启动",
        ),
        build_smtp_status(smtp),
        build_ai_status(ai),
        FeatureStatus(
            "监控项目",
            bool(config.projects),
            f"{len(config.projects)} 个",
            "" if config.projects else "在 config.yaml 的 projects 中添加工作区",
        ),
        FeatureStatus(
            "数据库",
            True,
            str(resolve_database_path(config.database_path)),
        ),
    ]
    if log_session_dir is not None:
        items.append(
            FeatureStatus(
                "日志",
                True,
                str(log_session_dir),
                "app.log · error.log · ai.log",
            )
        )
    else:
        items.append(
            FeatureStatus(
                "日志",
                False,
                str(resolve_log_root(config.log_dir)),
                "未能创建会话目录",
            )
        )
    return items


def print_startup_status(
    config: AppConfig,
    smtp: OperationalSmtp,
    ai: OperationalAi,
    *,
    config_path: Path,
    config_found: bool,
    log_session_dir: Path | None,
) -> None:
    console = make_console()
    table = Table(show_header=True, header_style="banner.title", expand=True, box=None)
    table.add_column("功能", style="label", no_wrap=True)
    table.add_column("状态", no_wrap=True)
    table.add_column("说明")

    for item in build_feature_statuses(
        config,
        smtp,
        ai,
        config_path=config_path,
        config_found=config_found,
        log_session_dir=log_session_dir,
    ):
        if item.enabled:
            status_text = "[status.on]已启用[/status.on]"
        elif item.status_style == "status.warn":
            status_text = "[status.warn]自检失败[/status.warn]"
        else:
            status_text = "[status.off]未启用[/status.off]"
        detail = escape(item.detail)
        if item.hint:
            detail = f"{detail}\n[dim]{escape(item.hint)}[/dim]"
        table.add_row(item.name, status_text, detail)

    console.print()
    console.print(Panel(table, title="[banner.title]gitmail 启动配置[/banner.title]", border_style="dim"))
    console.print()
