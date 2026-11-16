from fastapi import APIRouter

from app.api.routes import (
    access,
    auth,
    crafts,
    knowledge,
    map_layers,
    me,
    media,
    password_change,
    secrets,
    settings,
    two_factor,
    usage,
    users,
    voice,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(password_change.router)
api_router.include_router(me.router)
api_router.include_router(two_factor.router)
api_router.include_router(access.router)
api_router.include_router(users.router)
api_router.include_router(crafts.router)
api_router.include_router(knowledge.router)
api_router.include_router(map_layers.router)
api_router.include_router(media.router)
api_router.include_router(secrets.router)
api_router.include_router(settings.router)
api_router.include_router(usage.router)
api_router.include_router(voice.router)
