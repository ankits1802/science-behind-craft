from fastapi import APIRouter

from app.api.routes import access, auth, secrets, settings, two_factor, usage, users

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(two_factor.router)
api_router.include_router(access.router)
api_router.include_router(users.router)
api_router.include_router(secrets.router)
api_router.include_router(settings.router)
api_router.include_router(usage.router)
