from __future__ import annotations

import logging

from app_main.ai.summarizer import ping_ai_api
from app_main.feature_runtime import OperationalAi, OperationalSmtp
from app_main.mail.sender import send_startup_test_email

logger = logging.getLogger(__name__)


def run_startup_checks(smtp: OperationalSmtp, ai: OperationalAi) -> None:
    """对已填写的 SMTP / AI 配置各执行一次连通性自检；失败则关闭该功能。"""
    if smtp.settings_filled:
        try:
            send_startup_test_email(smtp.settings)
            logger.info("SMTP 启动自检通过，已向 %s 发送测试邮件", smtp.smtp_user)
        except Exception as exc:
            smtp.enabled = False
            smtp.init_error = str(exc)
            logger.error("SMTP 启动自检失败，已关闭邮件通知: %s", exc)

    if ai.settings_filled:
        try:
            ping_ai_api(ai.settings)
            logger.info("AI 启动自检通过")
        except Exception as exc:
            ai.enabled = False
            ai.init_error = str(exc)
            logger.error("AI 启动自检失败，已关闭 AI 总结: %s", exc)
