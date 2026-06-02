#!/usr/bin/env python3
"""
Seed script for Eluven development and testing.

Usage:
    python scripts/seed.py --dev     # Seed development data
    python scripts/seed.py --test    # Seed test fixtures
    python scripts/seed.py --clear   # Clear all seeded data
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Allow imports from backend/ and load backend/.env when run from repo root
_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
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

PLATFORM_ORG_SLUG = "eluven"
MVP_MODULE_TYPES = ("external_paper_review", "student_paper_review")


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
    """Seed development data — sample org, user, tasks, and cluster."""
    async with AsyncSessionLocal() as session:
        org, _ = await _get_or_create_org(
            session,
            name="Dev Org",
            slug="dev-org",
        )

        user, _ = await _get_or_create_user(
            session,
            org=org,
            email="dev@eluven.ai",
            name="Dev User",
            role=UserRole.APP_ADMIN,
            password="devpassword123",
        )

        paper_review = await session.execute(
            select(Task).where(
                Task.owner_id == user.id,
                Task.title == "Sample Paper Review",
                Task.module_type == "external_paper_review",
            )
        )
        if paper_review.scalar_one_or_none() is None:
            session.add(
                Task(
                    org_id=org.id,
                    owner_id=user.id,
                    title="Sample Paper Review",
                    module_type="external_paper_review",
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
                Task.module_type == "student_paper_review",
            )
        )
        if submission_result.scalar_one_or_none() is None:
            session.add(
                Task(
                    org_id=org.id,
                    owner_id=user.id,
                    cluster_id=cluster.id,
                    title="Sample Submission",
                    module_type="student_paper_review",
                    status=TaskStatus.DRAFT,
                )
            )
            _logger().info("seed_task_created", title="Sample Submission", cluster_id=str(cluster.id))
        else:
            _logger().info("seed_task_exists", title="Sample Submission")

        await session.commit()

    _logger().info("seed_dev_complete")


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


def _cli_args(*, dev: bool = False, test: bool = False, clear: bool = False) -> argparse.Namespace:
    return argparse.Namespace(dev=dev, test=test, clear=clear)


def seed_dev() -> None:
    """Seed development data — sample tasks, users, documents."""
    configure_logging()
    _logger().info("seed_dev_starting")
    asyncio.run(_run(_cli_args(dev=True)))


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


async def _run(args: argparse.Namespace) -> None:
    """Run the selected seed command and dispose the engine."""
    try:
        if args.dev:
            await _seed_dev_async()
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
    group.add_argument("--dev", action="store_true", help="Seed development data")
    group.add_argument("--test", action="store_true", help="Seed test fixtures")
    group.add_argument("--clear", action="store_true", help="Clear seeded data")

    args = parser.parse_args()

    if args.dev:
        _logger().info("seed_dev_starting")
    elif args.test:
        _logger().info("seed_test_starting")
    elif args.clear:
        _logger().info("seed_clear_starting")

    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
