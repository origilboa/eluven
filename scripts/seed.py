#!/usr/bin/env python3
"""
Seed script for Eluven development and testing.

Usage:
    python scripts/seed.py --dev     # Seed development data
    python scripts/seed.py --test    # Seed test fixtures
    python scripts/seed.py --clear   # Clear all seeded data
"""

import argparse
import sys


def seed_dev() -> None:
    """Seed development data — sample tasks, users, documents."""
    print("Seeding development data...")
    # TODO: Add during data model session
    # - Create dev user
    # - Create sample External Paper Review task
    # - Create sample Student Paper Review assignment
    # - Create sample cluster
    print("Dev seed complete.")


def seed_test() -> None:
    """Seed test fixtures — minimal data for automated tests."""
    print("Seeding test fixtures...")
    # TODO: Add during data model session
    # - Create test user
    # - Create minimal task per module type
    print("Test seed complete.")


def clear() -> None:
    """Clear all seeded data."""
    print("Clearing seeded data...")
    # TODO: Add during data model session
    print("Clear complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eluven seed script")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dev", action="store_true", help="Seed development data")
    group.add_argument("--test", action="store_true", help="Seed test fixtures")
    group.add_argument("--clear", action="store_true", help="Clear seeded data")

    args = parser.parse_args()

    if args.dev:
        seed_dev()
    elif args.test:
        seed_test()
    elif args.clear:
        clear()


if __name__ == "__main__":
    main()
