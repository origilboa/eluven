#!/usr/bin/env python3
"""Validate KB upload → indexing → RAG readiness against a running API."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent / "backend" / "tests" / "fixtures" / "sample.txt"


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    json_body: dict[str, object] | None = None,
    multipart: tuple[str, bytes, str] | None = None,
) -> dict[str, object]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data: bytes | None = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if multipart is not None:
        filename, payload, content_type = multipart
        boundary = "----eluven-validation"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8") + payload + f"\r\n--{boundary}--\r\n".encode("utf-8")
        data = body
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate KB indexing pipeline")
    parser.add_argument(
        "--base-url",
        default="https://app.eluven.ai/api/backend",
        help="API base URL (via frontend proxy or direct API URL)",
    )
    parser.add_argument("--email", default="dev@eluven.ai")
    parser.add_argument("--password", default="devpassword123")
    parser.add_argument("--poll-seconds", type=int, default=120)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    if not FIXTURE.exists():
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text("Sample knowledge base document for MVP validation.\n")

    try:
        login = _request(
            "POST",
            f"{base}/api/v1/auth/login",
            json_body={"email": args.email, "password": args.password},
        )
        token = str(login["access_token"])

        collection = _request(
            "POST",
            f"{base}/api/v1/kb/collections",
            token=token,
            json_body={"name": f"MVP validation {int(time.time())}"},
        )
        collection_id = str(collection["id"])

        upload = _request(
            "POST",
            f"{base}/api/v1/kb/collections/{collection_id}/documents",
            token=token,
            multipart=("sample.txt", FIXTURE.read_bytes(), "text/plain"),
        )
        document_id = str(upload["id"])

        deadline = time.time() + args.poll_seconds
        status = "pending"
        while time.time() < deadline:
            documents = _request(
                "GET",
                f"{base}/api/v1/kb/collections/{collection_id}/documents",
                token=token,
            )
            items = documents if isinstance(documents, list) else []
            match = next((item for item in items if str(item.get("id")) == document_id), None)
            status = str(match.get("status")) if match else "missing"
            if status == "ready":
                print(
                    json.dumps(
                        {
                            "event": "kb_rag_validation_passed",
                            "collection_id": collection_id,
                            "document_id": document_id,
                        },
                    ),
                )
                return 0
            if status == "failed":
                print(json.dumps({"event": "kb_rag_validation_failed", "reason": status}))
                return 1
            time.sleep(5)

        print(
            json.dumps(
                {
                    "event": "kb_rag_validation_failed",
                    "reason": "timeout",
                    "last_status": status,
                    "hint": "Ensure DocumentWorker ECS service is running",
                },
            ),
        )
        return 1
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(json.dumps({"event": "kb_rag_validation_failed", "http_status": exc.code, "body": body}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
