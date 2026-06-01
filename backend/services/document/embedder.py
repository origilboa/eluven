"""Document embedding via AWS Bedrock Titan."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from typing import Any

import boto3  # pyright: ignore[reportMissingTypeStubs]
from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

EMBEDDING_DIMENSIONS = 1536


class DocumentEmbedder:
    """Generate vector embeddings using Amazon Titan Embed Text v1."""

    def __init__(self, bedrock_client: Any | None = None) -> None:
        self._model_id = settings.bedrock_embed_model_id
        self._batch_size = settings.embed_batch_size
        self._client = bedrock_client or boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of text strings; returns 1536-dimensional vectors.

        Args:
            texts: Text chunks to embed.

        Returns:
            List of embedding vectors aligned with input texts.
        """
        if not texts:
            logger.info("document_embed_empty_input")
            return []

        logger.info("document_embed_started", text_count=len(texts), model_id=self._model_id)
        embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), self._batch_size):
            batch = texts[batch_start : batch_start + self._batch_size]
            batch_index = batch_start // self._batch_size
            logger.info(
                "document_embed_batch_started",
                batch_index=batch_index,
                batch_size=len(batch),
            )
            for text in batch:
                embeddings.append(self._embed_single(text))
            logger.info(
                "document_embed_batch_complete",
                batch_index=batch_index,
                batch_size=len(batch),
            )

        logger.info("document_embed_complete", text_count=len(texts), vector_count=len(embeddings))
        return embeddings

    def _embed_single(self, text: str) -> list[float]:
        """Invoke Bedrock for a single text input."""
        body = json.dumps({"inputText": text})
        try:
            response = self._client.invoke_model(
                modelId=self._model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(response["body"].read())
        except ClientError as exc:
            logger.exception("document_embed_failed", model_id=self._model_id)
            raise RuntimeError("Bedrock embedding request failed") from exc

        raw_embedding = payload.get("embedding")
        if not isinstance(raw_embedding, list):
            raise RuntimeError("Bedrock response missing embedding vector")

        embedding: list[Any] = raw_embedding
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Expected {EMBEDDING_DIMENSIONS} dimensions, got {len(embedding)}",
            )

        return [float(value) for value in embedding]
