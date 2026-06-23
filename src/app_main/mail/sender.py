from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app_main.ai.formatting import ai_summary_to_html, ai_summary_to_plain
from app_main.env_settings import SmtpSettings
from app_main.manifest.gerrit_urls import build_gerrit_urls
from app_main.models.repo import CommitInfo, RepoSnapshot


def send_plain_email(
    smtp: SmtpSettings,
    to_addr: str,
    subject: str,
    text_body: str,
) -> None:
    """发送纯文本邮件。"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp.smtp_from or smtp.smtp_user
    msg["To"] = to_addr
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    with smtplib.SMTP(smtp.smtp_host, smtp.smtp_port, timeout=60) as client:
        if smtp.smtp_use_tls:
            client.starttls()
        client.login(smtp.smtp_user, smtp.smtp_password)
        client.sendmail(msg["From"], [to_addr], msg.as_string())


def send_startup_test_email(smtp: SmtpSettings) -> None:
    """向 SMTP 账号自身发送一封启动自检邮件。"""
    to_addr = smtp.smtp_user.strip()
    if "@" not in to_addr:
        raise ValueError(f"SMTP_USER 不是有效邮箱地址: {to_addr}")
    send_plain_email(
        smtp,
        to_addr,
        "[gitmail] 启动自检",
        "gitmail 邮件通道启动自检成功。\n\n若收到此邮件，说明 SMTP 配置可用。",
    )


def send_repo_update_email(
    smtp: SmtpSettings,
    to_addr: str,
    repo: RepoSnapshot,
    commits: list[CommitInfo],
    ai_summary: str | None = None,
) -> None:
    """向单个收件人发送仓库更新邮件。"""
    if not smtp.configured:
        return
    subject = f"[gitmail] {repo.project_name} > {repo.repo_path} 有更新"
    text_body = _build_text_body(repo, commits, ai_summary)
    html_body = _build_html_body(repo, commits, ai_summary)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp.smtp_from or smtp.smtp_user
    msg["To"] = to_addr
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP(smtp.smtp_host, smtp.smtp_port, timeout=60) as client:
        if smtp.smtp_use_tls:
            client.starttls()
        client.login(smtp.smtp_user, smtp.smtp_password)
        client.sendmail(msg["From"], [to_addr], msg.as_string())


def _build_text_body(
    repo: RepoSnapshot,
    commits: list[CommitInfo],
    ai_summary: str | None = None,
) -> str:
    lines = [
        f"项目: {repo.project_name}",
        f"仓库: {repo.repo_path}",
        "",
        "最近提交:",
    ]
    for commit in commits:
        urls = build_gerrit_urls(repo.gerrit_base, repo.gerrit_project, commit.hash)
        lines.append(f"- {commit.hash[:12]} {commit.author} {commit.subject}")
        if urls.commit_url:
            lines.append(f"  {urls.commit_url}")
    if ai_summary:
        lines.extend(["", "AI 总结:", ai_summary_to_plain(ai_summary)])
    if repo.gerrit_project_url:
        lines.extend(["", f"Gerrit 项目页: {repo.gerrit_project_url}"])
    return "\n".join(lines)


def _build_html_body(
    repo: RepoSnapshot,
    commits: list[CommitInfo],
    ai_summary: str | None = None,
) -> str:
    items = []
    for commit in commits:
        urls = build_gerrit_urls(repo.gerrit_base, repo.gerrit_project, commit.hash)
        link = (
            f'<a href="{urls.commit_url}">{commit.hash[:12]}</a>'
            if urls.commit_url
            else commit.hash[:12]
        )
        items.append(f"<li>{link} {commit.author} — {commit.subject}</li>")
    project_link = ""
    if repo.gerrit_project_url:
        project_link = f'<p><a href="{repo.gerrit_project_url}">Gerrit 项目页</a></p>'
    summary_block = ""
    if ai_summary:
        summary_html = ai_summary_to_html(ai_summary)
        summary_block = (
            '<div style="margin-top:1em">'
            "<p><strong>AI 总结</strong></p>"
            f'<div style="line-height:1.5">{summary_html}</div>'
            "</div>"
        )
    return (
        f"<p><strong>{repo.project_name}</strong> &gt; {repo.repo_path}</p>"
        f"<ul>{''.join(items)}</ul>{summary_block}{project_link}"
    )
