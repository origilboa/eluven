#!/usr/bin/env python3
"""
Seed script for Eluven development and testing.

Usage:
    python scripts/seed.py --dev     # Minimal dev user + sample tasks (API startup)
    python scripts/seed.py --demo    # Rich demo dataset — 3 roles, tasks, threads, KB, workflows
    python scripts/seed.py --instructions  # Sample cluster/task instructions only
    python scripts/seed.py --reset-demo   # Wipe + migration seeds + full demo dataset
    python scripts/seed.py --test    # Seed test fixtures
    python scripts/seed.py --clear   # Clear all seeded data
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
os.chdir(_BACKEND_DIR)

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal, engine
from core.logging import configure_logging, get_logger
from core.security import hash_password
from models import Base
from models.cluster import Cluster
from models.org import Org
from models.task import Task, TaskStatus
from models.user import User, UserRole
from seed.constants import (
    DEV_ORG_NAME,
    DEV_ORG_SLUG,
    DEV_USER_EMAIL,
    DEV_USER_NAME,
    DEV_USER_PASSWORD,
    MVP_MODULE_EPR,
    MVP_MODULE_SPR,
    PLATFORM_ORG_SLUG,
    ORG_ADMIN_USER_EMAIL,
    ORG_ADMIN_USER_NAME,
    ORG_ADMIN_USER_PASSWORD,
    REVIEWER_USER_EMAIL,
    REVIEWER_USER_NAME,
    REVIEWER_USER_PASSWORD,
)
from seed.demo import seed_demo_async
from seed.instructions import seed_sample_instructions_async

MVP_MODULE_TYPES = (MVP_MODULE_EPR, MVP_MODULE_SPR)


def _logger():
    return get_logger(__name__)


async def _get_org_by_slug(session: AsyncSession, slug: str) -> Org | None:
    result = await session.execute(select(Org).where(Org.slug == slug))
    return result.scalar_one_or_none()


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _get_or_create_org(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
) -> tuple[Org, bool]:
    org = await _get_org_by_slug(session, slug)
    if org is not None:
        _logger().info("seed_org_exists", slug=slug, org_id=str(org.id))
        return org, False

    org = Org(name=name, slug=slug)
    session.add(org)
    await session.flush()
    _logger().info("seed_org_created", slug=slug, org_id=str(org.id))
    return org, True


async def _get_or_create_user(
    session: AsyncSession,
    *,
    org: Org,
    email: str,
    name: str,
    role: UserRole,
    password: str,
) -> tuple[User, bool]:
    user = await _get_user_by_email(session, email)
    if user is not None:
        _logger().info("seed_user_exists", email=email, user_id=str(user.id))
        return user, False

    user = User(
        org_id=org.id,
        email=email,
        name=name,
        role=role,
        hashed_password=hash_password(password),
    )
    session.add(user)
    await session.flush()
    _logger().info("seed_user_created", email=email, user_id=str(user.id), role=role.value)
    return user, True


async def _seed_dev_async() -> None:
    """Seed minimal development data — dev user, reviewer user, basic tasks."""
    async with AsyncSessionLocal() as session:
        org, _ = await _get_or_create_org(
            session,
            name=DEV_ORG_NAME,
            slug=DEV_ORG_SLUG,
        )

        user, _ = await _get_or_create_user(
            session,
            org=org,
            email=DEV_USER_EMAIL,
            name=DEV_USER_NAME,
            role=UserRole.APP_ADMIN,
            password=DEV_USER_PASSWORD,
        )

        await _get_or_create_user(
            session,
            org=org,
            email=ORG_ADMIN_USER_EMAIL,
            name=ORG_ADMIN_USER_NAME,
            role=UserRole.ORG_ADMIN,
            password=ORG_ADMIN_USER_PASSWORD,
        )

        await _get_or_create_user(
            session,
            org=org,
            email=REVIEWER_USER_EMAIL,
            name=REVIEWER_USER_NAME,
            role=UserRole.USER,
            password=REVIEWER_USER_PASSWORD,
        )

        paper_review = await session.execute(
            select(Task).where(
                Task.owner_id == user.id,
                Task.title == "Sample Paper Review",
                Task.module_type == MVP_MODULE_EPR,
            )
        )
        if paper_review.scalar_one_or_none() is None:
            session.add(
                Task(
                    org_id=org.id,
                    owner_id=user.id,
                    title="Sample Paper Review",
                    module_type=MVP_MODULE_EPR,
                    status=TaskStatus.DRAFT,
                )
            )
            _logger().info("seed_task_created", title="Sample Paper Review")
        else:
            _logger().info("seed_task_exists", title="Sample Paper Review")

        cluster_result = await session.execute(
            select(Cluster).where(
                Cluster.owner_id == user.id,
                Cluster.name == "Sample Assignment",
                Cluster.cluster_type == "assignment",
            )
        )
        cluster = cluster_result.scalar_one_or_none()
        if cluster is None:
            cluster = Cluster(
                org_id=org.id,
                owner_id=user.id,
                name="Sample Assignment",
                cluster_type="assignment",
            )
            session.add(cluster)
            await session.flush()
            _logger().info(
                "seed_cluster_created",
                name="Sample Assignment",
                cluster_id=str(cluster.id),
            )
        else:
            _logger().info("seed_cluster_exists", name="Sample Assignment")

        submission_result = await session.execute(
            select(Task).where(
                Task.cluster_id == cluster.id,
                Task.module_type == MVP_MODULE_SPR,
            )
        )
        if submission_result.scalar_one_or_none() is None:
            session.add(
                Task(
                    org_id=org.id,
                    owner_id=user.id,
                    cluster_id=cluster.id,
                    title="Sample Submission",
                    module_type=MVP_MODULE_SPR,
                    status=TaskStatus.DRAFT,
                )
            )
            _logger().info("seed_task_created", title="Sample Submission", cluster_id=str(cluster.id))
        else:
            _logger().info("seed_task_exists", title="Sample Submission")

        await session.commit()

    _logger().info("seed_dev_complete")


async def _seed_instructions_wrapper_async() -> None:
    """Seed sample cluster/task instructions only (existing entities)."""
    async with AsyncSessionLocal() as session:
        await seed_sample_instructions_async(session)
    _logger().info("seed_instructions_wrapper_complete")


async def _seed_demo_wrapper_async() -> None:
    """Seed full demo dataset (includes dev org and both users)."""
    async with AsyncSessionLocal() as session:
        await seed_demo_async(session)
    _logger().info("seed_demo_wrapper_complete")


async def _seed_test_async() -> None:
    """Seed minimal test fixtures — one task per MVP module type."""
    async with AsyncSessionLocal() as session:
        org, _ = await _get_or_create_org(
            session,
            name="Test Org",
            slug="test-org",
        )

        user, _ = await _get_or_create_user(
            session,
            org=org,
            email="test@eluven.ai",
            name="Test User",
            role=UserRole.USER,
            password="testpassword123",
        )

        for module_type in MVP_MODULE_TYPES:
            existing = await session.execute(
                select(Task).where(
                    Task.owner_id == user.id,
                    Task.module_type == module_type,
                    Task.title == f"Test {module_type}",
                )
            )
            if existing.scalar_one_or_none() is not None:
                _logger().info("seed_task_exists", module_type=module_type)
                continue

            session.add(
                Task(
                    org_id=org.id,
                    owner_id=user.id,
                    title=f"Test {module_type}",
                    module_type=module_type,
                    status=TaskStatus.DRAFT,
                )
            )
            _logger().info("seed_task_created", module_type=module_type)

        await session.commit()

    _logger().info("seed_test_complete")


async def _clear_async() -> None:
    """Remove all seeded data; preserve platform org and Alembic version."""
    tables_to_truncate = [
        table.name
        for table in Base.metadata.sorted_tables
        if table.name not in ("alembic_version", "orgs")
    ]

    async with AsyncSessionLocal() as session:
        if tables_to_truncate:
            quoted = ", ".join(f'"{name}"' for name in tables_to_truncate)
            await session.execute(
                text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
            )
            _logger().info("seed_truncated_tables", table_count=len(tables_to_truncate))

        result = await session.execute(
            text("DELETE FROM orgs WHERE slug != :slug"),
            {"slug": PLATFORM_ORG_SLUG},
        )
        _logger().info("seed_deleted_orgs", rowcount=result.rowcount)

        await session.commit()

    _logger().info("seed_clear_complete")


def _alembic_database_url() -> str:
    """Sync PostgreSQL URL for Alembic (strips asyncpg driver)."""
    env_file = _BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

    url = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _run_alembic_migrations(*args: str) -> None:
    """Run alembic CLI with DATABASE_URL from environment."""
    env = os.environ.copy()
    env["DATABASE_URL"] = _alembic_database_url()
    cmd = ["alembic", *args]
    _logger().info("alembic_command_start", command=" ".join(cmd))
    subprocess.run(cmd, cwd=_BACKEND_DIR, check=True, env=env)
    _logger().info("alembic_command_complete", command=" ".join(cmd))


async def _reset_demo_async() -> None:
    """Wipe app data, re-apply migration seeds, load full demo dataset."""
    _logger().info("reset_demo_starting")
    _run_alembic_migrations("downgrade", "001")
    _logger().info("reset_demo_database_wiped")
    _run_alembic_migrations("upgrade", "head")
    _logger().info("reset_demo_migrations_applied")
    await _seed_demo_wrapper_async()
    _logger().info("reset_demo_complete")


def reset_demo() -> None:
    """Reset DB: migration seeds + full demo sample data."""
    configure_logging()
    _logger().info("reset_demo_cli_starting")
    asyncio.run(_run(_cli_args(reset_demo=True)))


def seed_dev() -> None:
    """Seed development data — sample tasks, users, documents."""
    configure_logging()
    _logger().info("seed_dev_starting")
    asyncio.run(_run(_cli_args(dev=True)))


def seed_instructions() -> None:
    """Seed sample cluster and task instructions for demo/test entities."""
    configure_logging()
    _logger().info("seed_instructions_starting")
    asyncio.run(_run(_cli_args(instructions=True)))


def seed_demo() -> None:
    """Seed rich demo dataset for manual testing."""
    configure_logging()
    _logger().info("seed_demo_starting")
    asyncio.run(_run(_cli_args(demo=True)))


def seed_test() -> None:
    """Seed test fixtures — minimal data for automated tests."""
    configure_logging()
    _logger().info("seed_test_starting")
    asyncio.run(_run(_cli_args(test=True)))


def clear() -> None:
    """Clear all seeded data except the platform org."""
    configure_logging()
    _logger().info("seed_clear_starting")
    asyncio.run(_run(_cli_args(clear=True)))


def _cli_args(
    *,
    dev: bool = False,
    demo: bool = False,
    instructions: bool = False,
    reset_demo: bool = False,
    test: bool = False,
    clear: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        dev=dev,
        demo=demo,
        instructions=instructions,
        reset_demo=reset_demo,
        test=test,
        clear=clear,
    )


async def _run(args: argparse.Namespace) -> None:
    """Run the selected seed command and dispose the engine."""
    try:
        if args.dev:
            await _seed_dev_async()
        elif args.reset_demo:
            await _reset_demo_async()
        elif args.demo:
            await _seed_demo_wrapper_async()
        elif args.instructions:
            await _seed_instructions_wrapper_async()
        elif args.test:
            await _seed_test_async()
        elif args.clear:
            await _clear_async()
    finally:
        await engine.dispose()


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Eluven seed script")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dev", action="store_true", help="Seed minimal development data")
    group.add_argument(
        "--demo",
        action="store_true",
        help="Seed rich demo dataset (3 roles, tasks, threads, KB, workflows)",
    )
    group.add_argument(
        "--instructions",
        action="store_true",
        help="Seed sample cluster/task instructions on demo entities and task titled 'test'",
    )
    group.add_argument(
        "--reset-demo",
        action="store_true",
        help="Reset DB: re-run migration seeds + full demo dataset (destructive)",
    )
    group.add_argument("--test", action="store_true", help="Seed test fixtures")
    group.add_argument("--clear", action="store_true", help="Clear seeded data")

    args = parser.parse_args()

    if args.dev:
        _logger().info("seed_dev_starting")
    elif args.reset_demo:
        _logger().info("reset_demo_starting")
    elif args.demo:
        _logger().info("seed_demo_starting")
    elif args.instructions:
        _logger().info("seed_instructions_starting")
    elif args.test:
        _logger().info("seed_test_starting")
    elif args.clear:
        _logger().info("seed_clear_starting")

    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
