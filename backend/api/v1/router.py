"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from api.v1 import auth, clusters, kb, tasks, threads

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(kb.router)
router.include_router(clusters.router)
router.include_router(tasks.router)
router.include_router(threads.router)
