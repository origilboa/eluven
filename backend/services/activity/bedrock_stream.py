"""Shared Bedrock streaming helpers for Layer 0 activity agents."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import AsyncIterator
from typing import Any

from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]

from core.config import settings


async def stream_bedrock_text(
    *,
    bedrock_client: Any,
    model_id: str,
    system_text: str,
    messages: list[dict[str, str]],
) -> AsyncIterator[str | dict[str, Any]]:
    """Stream text deltas and a final done payload from Bedrock."""
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": settings.bedrock_max_output_tokens,
        "system": system_text,
        "messages": messages,
    }

    input_tokens = 0
    output_tokens = 0
    cached_tokens = 0

    try:
        async for event in _stream_events(bedrock_client, model_id, request_body):
            chunk_type = event.get("type")
            if chunk_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        yield text
            elif chunk_type == "message_delta":
                usage = event.get("usage", {})
                output_tokens = int(usage.get("output_tokens", output_tokens))
            elif chunk_type == "message_start":
                message_usage = event.get("message", {}).get("usage", {})
                input_tokens = int(message_usage.get("input_tokens", input_tokens))
                cached_tokens = int(
                    message_usage.get("cache_read_input_tokens", cached_tokens),
                )
    except ClientError as exc:
        raise RuntimeError("Bedrock streaming request failed") from exc

    yield {
        "type": "done",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
        "model_id": model_id,
    }


async def _stream_events(
    bedrock_client: Any,
    model_id: str,
    request_body: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

    def _producer() -> None:
        try:
            response = bedrock_client.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )
            for event in response["body"]:
                chunk_bytes = event.get("chunk", {}).get("bytes")
                if chunk_bytes:
                    payload = json.loads(chunk_bytes)
                    loop.call_soon_threadsafe(queue.put_nowait, ("event", payload))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

    worker = threading.Thread(target=_producer, daemon=True)
    worker.start()

    while True:
        kind, payload = await queue.get()
        if kind == "done":
            break
        if kind == "error":
            raise payload
        yield payload
