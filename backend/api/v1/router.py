"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from api.v1 import auth

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["auth"])
