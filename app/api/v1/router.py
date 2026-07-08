from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.kiosk.router import router as kiosk_router
from app.api.v1.me.router import router as me_router
from app.api.v1.account.related_persons import router as account_related_persons_router
from app.api.v1.admin.submissions import router as admin_submissions_router
from app.api.v1.admin.print_jobs import router as admin_print_jobs_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(kiosk_router)
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(account_related_persons_router)
api_router.include_router(admin_submissions_router)
api_router.include_router(admin_print_jobs_router)