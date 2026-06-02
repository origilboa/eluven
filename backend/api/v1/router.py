"""API v1 router aggregating all sub-routers."""

from fastapi import APIRouter

from api.v1 import (
    activity_library,
    admin,
    admin_activity_library,
    auth,
    clusters,
    instructions,
    kb,
    tasks,
    threads,
    workflows,
)

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(admin.router)
router.include_router(admin_activity_library.router)
router.include_router(kb.router)
router.include_router(clusters.router)
router.include_router(tasks.router)
router.include_router(threads.router)
router.include_router(workflows.router)
router.include_router(activity_library.router)
router.include_router(instructions.router)
