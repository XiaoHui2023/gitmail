from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app_main.api import router as api_router
from app_main.api.deps import AppState
from app_main.config_loader import load_config, resolve_config_path
from app_main.env_settings import AiSettings, SmtpSettings
from app_main.feature_runtime import OperationalAi, OperationalSmtp
from app_main.mail.notifier import Notifier
from app_main.monitor.service import MonitorService
from app_main.paths import resolve_database_path, resolve_frontend_dist
from app_main.store.database import Store
from app_main.webhooks.dispatcher import WebhookDispatcher

logger = logging.getLogger(__name__)

_config_path: Path | None = None


def set_config_path(path: Path | None) -> None:
    global _config_path
    _config_path = path


def _build_inner_app(ctx: AppState) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ctx.monitor.start()
        logger.info("监控调度已启动")
        yield
        ctx.monitor.stop()
        ctx.store.close()
        logger.info("监控调度已停止")

    app = FastAPI(title="gitmail", lifespan=lifespan)
    app.state.ctx = ctx
    app.include_router(api_router)

    dist = resolve_frontend_dist()
    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        file_path = dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index = dist / "index.html"
        return FileResponse(index)

    return app


def create_app(
    config_path: Path | None = None,
    *,
    smtp: OperationalSmtp | None = None,
    ai: OperationalAi | None = None,
) -> FastAPI:
    """创建 FastAPI 应用并挂载 API 与前端静态资源。"""
    path = config_path or _config_path or resolve_config_path(None)
    if path.is_file():
        config = load_config(path)
    else:
        from app_main.models.config import AppConfig

        config = AppConfig(email_domain="example.com", projects=[])
        logger.warning("未找到配置文件 %s，使用空配置", path)

    store = Store(resolve_database_path(config.database_path))
    smtp = smtp or OperationalSmtp(SmtpSettings())
    ai = ai or OperationalAi(AiSettings())
    notifier = Notifier(store, config, smtp)
    webhooks = WebhookDispatcher(store)
    monitor = MonitorService(config, store, notifier, ai, webhooks)
    ctx = AppState(config=config, store=store, monitor=monitor, smtp=smtp, ai=ai, webhooks=webhooks)

    prefix = config.public_base_path.strip().rstrip("/")
    inner = _build_inner_app(ctx)
    if not prefix:
        return inner

    root = FastAPI(title="gitmail-root")
    root.mount(prefix, inner)
    return root
