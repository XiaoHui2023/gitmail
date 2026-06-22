from fastapi import APIRouter

from app_main.api.repos import router as repos_router
from app_main.api.settings import router as settings_router
from app_main.api.status import router as status_router
from app_main.api.subscriptions import router as subscriptions_router
from app_main.api.user import router as user_router
from app_main.api.webhooks import router as webhooks_router

router = APIRouter(prefix="/api", tags=["api"])
router.include_router(status_router)
router.include_router(repos_router)
router.include_router(user_router)
router.include_router(subscriptions_router)
router.include_router(settings_router)
router.include_router(webhooks_router)
