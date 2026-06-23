from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app_main.api.deps import AppState, get_app_state
from app_main.monitor.service import MonitorHealth

router = APIRouter(tags=["status"])


@router.get("/status")
def get_status(state: Annotated[AppState, Depends(get_app_state)]) -> dict:
    if not state.monitor.is_running():
        raise HTTPException(status_code=503, detail="监控调度未运行")
    health: MonitorHealth = state.monitor.health
    return {
        "ok": True,
        "name": "gitmail",
        "monitor": {
            "running": health.running,
            "last_round_seconds": health.last_round_seconds,
            "last_round_repo_count": health.last_round_repo_count,
            "failed_repo_count": health.failed_repo_count,
            "project_errors": health.project_errors,
        },
        "frontend_poll_seconds": state.config.frontend_poll_seconds,
        "public_base_path": state.config.public_base_path,
    }
