#!/usr/bin/env python3
"""Run MVP success-criteria validation checklist against production."""

from __future__ import annotations

import argparse
import subprocess
import sys


CHECKS: list[tuple[str, list[str]]] = [
    ("KB upload and indexing (txt)", [sys.executable, "scripts/validate_mvp_kb_rag.py"]),
    (
        "KB upload and indexing (pdf)",
        [sys.executable, "scripts/validate_mvp_kb_rag.py", "--fixture", "pdf"],
    ),
    (
        "KB upload and indexing (docx)",
        [sys.executable, "scripts/validate_mvp_kb_rag.py", "--fixture", "docx"],
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="MVP validation checklist runner")
    parser.add_argument("--base-url", default="https://app.eluven.ai/api/backend")
    args = parser.parse_args()

    failures = 0
    for name, command in CHECKS:
        print(f"Running: {name}")
        result = subprocess.run(
            [*command, "--base-url", args.base_url],
            check=False,
        )
        if result.returncode != 0:
            failures += 1
            print(f"FAILED: {name}")
        else:
            print(f"PASSED: {name}")

    print(f"\nMVP automated checks complete: {len(CHECKS) - failures}/{len(CHECKS)} passed")
    print(
        "Manual checks still required: one full EPR task, one full SPR task, "
        "instruction quality review, UX friction notes."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
