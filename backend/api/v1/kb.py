"""Knowledge base API endpoints (data model Section 10.5)."""

from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from starlette.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_current_active_user, get_db
from core.logging import get_logger
from models.cluster import Cluster
from models.kb import (
    KBCollection,
    KBCollectionAttachment,
    KBDocument,
    KBDocumentStatus,
)
from models.task import Task
from models.user import User
from schemas.kb import (
    AttachCollectionRequest,
    CreateCollectionRequest,
    KBAttachmentResponse,
    KBDocumentResponse,
    KBCollectionResponse,
    UpdateCollectionRequest,
)
from services.document.constants import SUPPORTED_FILE_TYPES
from services.document_queue import enqueue_document_processing
from services.storage import StorageService

logger = get_logger(__name__)

router = APIRouter(prefix="/kb", tags=["kb"])

ENTITY_TYPE_TASK = "task"
ENTITY_TYPE_CLUSTER = "cluster"


def _file_type_from_filename(filename: str) -> str:
    if "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must include an extension",
        )
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {extension}",
        )
    return extension


def _content_type_for_file_type(file_type: str, filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    return "application/octet-stream"


async def _get_owned_collection(
    session: AsyncSession,
    collection_id: UUID,
    user: User,
) -> KBCollection:
    collection = await session.get(KBCollection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    if collection.org_id != user.org_id or collection.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection


async def _document_count(session: AsyncSession, collection_id: UUID) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(KBDocument)
        .where(
            KBDocument.collection_id == collection_id,
            KBDocument.is_deleted.is_(False),
        ),
    )
    return int(count or 0)


async def _active_document_count(session: AsyncSession, collection_id: UUID) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(KBDocument)
        .where(
            KBDocument.collection_id == collection_id,
            KBDocument.is_active.is_(True),
            KBDocument.is_deleted.is_(False),
        ),
    )
    return int(count or 0)


async def _entity_name(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: UUID,
    org_id: UUID,
) -> str:
    if entity_type == ENTITY_TYPE_TASK:
        task = await session.get(Task, entity_id)
        if task is None or task.org_id != org_id:
            return "Unknown"
        return task.title
    if entity_type == ENTITY_TYPE_CLUSTER:
        cluster = await session.get(Cluster, entity_id)
        if cluster is None or cluster.org_id != org_id:
            return "Unknown"
        return cluster.name
    return "Unknown"


async def _attachment_responses(
    session: AsyncSession,
    collection: KBCollection,
) -> list[KBAttachmentResponse]:
    result = await session.execute(
        select(KBCollectionAttachment)
        .where(KBCollectionAttachment.collection_id == collection.id)
        .order_by(KBCollectionAttachment.attached_at.asc()),
    )
    attachments = result.scalars().all()
    responses: list[KBAttachmentResponse] = []
    for attachment in attachments:
        name = await _entity_name(
            session,
            entity_type=attachment.entity_type,
            entity_id=attachment.entity_id,
            org_id=collection.org_id,
        )
        responses.append(
            KBAttachmentResponse(
                id=attachment.id,
                entity_type=attachment.entity_type,
                entity_id=attachment.entity_id,
                entity_name=name,
                attached_at=attachment.attached_at,
            ),
        )
    return responses


async def _collection_response(
    session: AsyncSession,
    collection: KBCollection,
    *,
    include_attachments: bool = True,
) -> KBCollectionResponse:
    doc_count = await _document_count(session, collection.id)
    attachments = (
        await _attachment_responses(session, collection) if include_attachments else []
    )
    return KBCollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        document_count=doc_count,
        attachments=attachments,
        created_at=collection.created_at,
    )


def _document_response(document: KBDocument) -> KBDocumentResponse:
    return KBDocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        size_bytes=document.size_bytes,
        status=document.status.value,
        chunk_count=document.chunk_count,
        version=document.version,
        created_at=document.created_at,
    )


async def _validate_attach_target(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: UUID,
    user: User,
) -> None:
    if entity_type == ENTITY_TYPE_TASK:
        task = await session.get(Task, entity_id)
        if task is None or task.org_id != user.org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return
    if entity_type == ENTITY_TYPE_CLUSTER:
        cluster = await session.get(Cluster, entity_id)
        if cluster is None or cluster.org_id != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cluster not found",
            )
        return
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity_type")


@router.get("/collections", response_model=list[KBCollectionResponse])
async def list_collections(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[KBCollectionResponse]:
    """List the current user's KB collections."""
    result = await db.execute(
        select(KBCollection)
        .where(
            KBCollection.org_id == current_user.org_id,
            KBCollection.owner_id == current_user.id,
        )
        .order_by(KBCollection.created_at.desc()),
    )
    collections = result.scalars().all()
    responses = [await _collection_response(db, collection) for collection in collections]
    logger.info("kb_collections_listed", user_id=str(current_user.id), count=len(responses))
    return responses


@router.post("/collections", response_model=KBCollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CreateCollectionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KBCollectionResponse:
    """Create a new KB collection."""
    collection = KBCollection(
        org_id=current_user.org_id,
        owner_id=current_user.id,
        name=body.name,
        description=body.description,
    )
    db.add(collection)
    await db.flush()

    logger.info(
        "kb_collection_created",
        collection_id=str(collection.id),
        user_id=str(current_user.id),
    )
    return await _collection_response(db, collection)


@router.get("/collections/{collection_id}", response_model=KBCollectionResponse)
async def get_collection(
    collection_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KBCollectionResponse:
    """Get collection detail including attachments."""
    collection = await _get_owned_collection(db, collection_id, current_user)
    return await _collection_response(db, collection)


@router.patch("/collections/{collection_id}", response_model=KBCollectionResponse)
async def update_collection(
    collection_id: UUID,
    body: UpdateCollectionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KBCollectionResponse:
    """Rename or update a collection."""
    collection = await _get_owned_collection(db, collection_id, current_user)
    collection.name = body.name
    if body.description is not None:
        collection.description = body.description

    logger.info("kb_collection_updated", collection_id=str(collection_id))
    return await _collection_response(db, collection)


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_collection(
    collection_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Delete a collection when it has no active documents."""
    collection = await _get_owned_collection(db, collection_id, current_user)
    active_count = await _active_document_count(db, collection_id)
    if active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection cannot be deleted while it has active documents",
        )

    await db.delete(collection)
    logger.info("kb_collection_deleted", collection_id=str(collection_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/collections/{collection_id}/documents",
    response_model=list[KBDocumentResponse],
)
async def list_documents(
    collection_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[KBDocumentResponse]:
    """List documents in a KB collection."""
    await _get_owned_collection(db, collection_id, current_user)

    result = await db.execute(
        select(KBDocument)
        .where(
            KBDocument.collection_id == collection_id,
            KBDocument.is_deleted.is_(False),
        )
        .order_by(KBDocument.created_at.desc()),
    )
    documents = result.scalars().all()
    return [_document_response(document) for document in documents]


@router.post(
    "/collections/{collection_id}/documents",
    response_model=KBDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    collection_id: UUID,
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KBDocumentResponse:
    """Upload a document, store in S3, and enqueue for processing."""
    collection = await _get_owned_collection(db, collection_id, current_user)

    filename = file.filename or "document"
    file_type = _file_type_from_filename(filename)
    file_bytes = await file.read()
    size_bytes = len(file_bytes)

    document_id = uuid4()
    s3_key = f"{current_user.org_id}/kb/{collection_id}/{document_id}/{filename}"
    content_type = _content_type_for_file_type(file_type, filename)

    document = KBDocument(
        id=document_id,
        org_id=current_user.org_id,
        collection_id=collection.id,
        filename=filename,
        s3_key=s3_key,
        size_bytes=size_bytes,
        file_type=file_type,
        status=KBDocumentStatus.PENDING,
        uploaded_by=current_user.id,
    )
    db.add(document)
    await db.flush()

    storage = StorageService()
    storage.upload_file(file_bytes, s3_key, content_type)

    logger.info(
        "document_upload",
        document_id=str(document_id),
        file_type=file_type,
        size_bytes=size_bytes,
        collection_id=str(collection_id),
    )

    enqueue_document_processing(document_id, "kb")

    return _document_response(document)


@router.delete(
    "/collections/{collection_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_document(
    collection_id: UUID,
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Soft-delete a KB document."""
    await _get_owned_collection(db, collection_id, current_user)

    document = await db.get(KBDocument, document_id)
    if (
        document is None
        or document.collection_id != collection_id
        or document.org_id != current_user.org_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document.is_deleted = True
    document.is_active = False
    document.deleted_at = datetime.now(UTC)

    logger.info("kb_document_deleted", document_id=str(document_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/collections/{collection_id}/attach",
    response_model=KBAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_collection(
    collection_id: UUID,
    body: AttachCollectionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KBAttachmentResponse:
    """Attach a collection to a Task or Cluster."""
    collection = await _get_owned_collection(db, collection_id, current_user)
    await _validate_attach_target(
        db,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        user=current_user,
    )

    existing = await db.execute(
        select(KBCollectionAttachment).where(
            KBCollectionAttachment.collection_id == collection_id,
            KBCollectionAttachment.entity_type == body.entity_type,
            KBCollectionAttachment.entity_id == body.entity_id,
        ),
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Collection is already attached to this entity",
        )

    attachment = KBCollectionAttachment(
        collection_id=collection_id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        attached_by=current_user.id,
    )
    db.add(attachment)
    await db.flush()

    entity_name = await _entity_name(
        db,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        org_id=collection.org_id,
    )

    logger.info(
        "kb_collection_attached",
        collection_id=str(collection_id),
        entity_type=body.entity_type,
        entity_id=str(body.entity_id),
    )

    return KBAttachmentResponse(
        id=attachment.id,
        entity_type=attachment.entity_type,
        entity_id=attachment.entity_id,
        entity_name=entity_name,
        attached_at=attachment.attached_at,
    )


@router.delete(
    "/collections/{collection_id}/attach/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def detach_collection(
    collection_id: UUID,
    attachment_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Detach a collection from a Task or Cluster."""
    await _get_owned_collection(db, collection_id, current_user)

    attachment = await db.get(KBCollectionAttachment, attachment_id)
    if attachment is None or attachment.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    await db.delete(attachment)
    logger.info(
        "kb_collection_detached",
        collection_id=str(collection_id),
        attachment_id=str(attachment_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
