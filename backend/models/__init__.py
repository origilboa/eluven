"""SQLAlchemy models and Section 9 database indexes."""

from sqlalchemy import Index

from models.activity import (
    ActivityLibraryEntry,
    QAResponseType,
    QAStage,
    ThreadQAQuestion,
    ThreadQAResponse,
)
from models.base import Base
from models.cluster import Cluster
from models.invitation import UserInvitation
from models.instruction import (
    InstructionLevel,
    InstructionSet,
    InstructionVersion,
    TaskInstructionOverride,
    TaskThreadTypeInstruction,
)
from models.kb import (
    DocumentChunk,
    KBCollection,
    KBCollectionAttachment,
    KBDocument,
    KBDocumentStatus,
    TaskDocument,
    ThreadDocument,
    ThreadDocumentLoadStrategy,
)
from models.memory import TaskMemoryEntry, TaskMemoryEntryType
from models.org import Org
from models.task import Task, TaskStatus, TaskTemplate
from models.thread import MessageRole, Thread, ThreadMessage, ThreadStatus
from models.user import User, UserRole
from models.workflow import (
    InterventionTriggerType,
    WorkflowExecution,
    WorkflowIntervention,
    WorkflowStatus,
    WorkflowTemplate,
    WorkflowThreadExecution,
    WorkflowThreadStatus,
)

__all__ = [
    "Base",
    "Org",
    "User",
    "UserRole",
    "UserInvitation",
    "Cluster",
    "Task",
    "TaskStatus",
    "TaskTemplate",
    "Thread",
    "ThreadStatus",
    "ThreadMessage",
    "MessageRole",
    "TaskMemoryEntry",
    "TaskMemoryEntryType",
    "InstructionSet",
    "InstructionVersion",
    "InstructionLevel",
    "TaskThreadTypeInstruction",
    "TaskInstructionOverride",
    "KBCollection",
    "KBCollectionAttachment",
    "KBDocument",
    "KBDocumentStatus",
    "TaskDocument",
    "ThreadDocument",
    "ThreadDocumentLoadStrategy",
    "DocumentChunk",
    "WorkflowTemplate",
    "WorkflowExecution",
    "WorkflowThreadExecution",
    "WorkflowIntervention",
    "WorkflowStatus",
    "WorkflowThreadStatus",
    "InterventionTriggerType",
    "ActivityLibraryEntry",
    "ThreadQAQuestion",
    "ThreadQAResponse",
    "QAStage",
    "QAResponseType",
    # Section 9 indexes
    "ix_thread_messages_thread_id_created_at",
    "ix_task_memory_entries_task_id",
    "ix_task_memory_entries_task_id_type",
    "ix_document_chunks_org_id_collection_id",
    "ix_document_chunks_thread_document_id",
    "ix_document_chunks_task_document_id",
    "ix_kb_collection_attachments_entity",
    "ix_kb_collections_org_id_is_org_collection",
    "ix_instruction_sets_task_id",
    "ix_instruction_sets_cluster_id",
    "ix_instruction_sets_user_id",
    "ix_instruction_sets_org_id",
    "ix_instruction_sets_thread_id",
    "ix_task_thread_type_instructions_task_id_thread_type",
    "ix_thread_qa_responses_thread_id",
    "ix_tasks_owner_id_status",
    "ix_tasks_cluster_id",
    "ix_threads_task_id_status",
    "ix_clusters_owner_id",
    "ix_clusters_org_id_cluster_type",
    "ix_kb_documents_status",
    "ix_kb_documents_collection_id_is_active",
    "ix_kb_documents_collection_id_active_deleted",
    "ix_kb_collections_owner_id",
    "ix_workflow_executions_task_id_status",
    "ix_workflow_thread_executions_workflow_execution_id_status",
    "ix_workflow_interventions_workflow_execution_id",
    "ix_user_invitations_org_id",
    "ix_user_invitations_email",
]

# Section 9.1 — Critical path (every AI call)
ix_thread_messages_thread_id_created_at = Index(
    "ix_thread_messages_thread_id_created_at",
    ThreadMessage.thread_id,
    ThreadMessage.created_at,
)
ix_task_memory_entries_task_id = Index(
    "ix_task_memory_entries_task_id",
    TaskMemoryEntry.task_id,
)
ix_task_memory_entries_task_id_type = Index(
    "ix_task_memory_entries_task_id_type",
    TaskMemoryEntry.task_id,
    TaskMemoryEntry.entry_type,
)
ix_document_chunks_org_id_collection_id = Index(
    "ix_document_chunks_org_id_collection_id",
    DocumentChunk.org_id,
    DocumentChunk.collection_id,
)
ix_document_chunks_thread_document_id = Index(
    "ix_document_chunks_thread_document_id",
    DocumentChunk.thread_document_id,
)
ix_document_chunks_task_document_id = Index(
    "ix_document_chunks_task_document_id",
    DocumentChunk.task_document_id,
)
ix_kb_collection_attachments_entity = Index(
    "ix_kb_collection_attachments_entity",
    KBCollectionAttachment.entity_type,
    KBCollectionAttachment.entity_id,
)
ix_kb_collections_org_id_is_org_collection = Index(
    "ix_kb_collections_org_id_is_org_collection",
    KBCollection.org_id,
    KBCollection.is_org_collection,
)
ix_instruction_sets_task_id = Index(
    "ix_instruction_sets_task_id",
    InstructionSet.task_id,
)
ix_instruction_sets_cluster_id = Index(
    "ix_instruction_sets_cluster_id",
    InstructionSet.cluster_id,
)
ix_instruction_sets_user_id = Index(
    "ix_instruction_sets_user_id",
    InstructionSet.user_id,
)
ix_instruction_sets_org_id = Index(
    "ix_instruction_sets_org_id",
    InstructionSet.owner_org_id,
)
ix_instruction_sets_thread_id = Index(
    "ix_instruction_sets_thread_id",
    InstructionSet.thread_id,
)
ix_task_thread_type_instructions_task_id_thread_type = Index(
    "ix_task_thread_type_instructions_task_id_thread_type",
    TaskThreadTypeInstruction.task_id,
    TaskThreadTypeInstruction.thread_type,
)
ix_thread_qa_responses_thread_id = Index(
    "ix_thread_qa_responses_thread_id",
    ThreadQAResponse.thread_id,
)

# Section 9.2 — Dashboard and navigation
ix_tasks_owner_id_status = Index(
    "ix_tasks_owner_id_status",
    Task.owner_id,
    Task.status,
)
ix_tasks_cluster_id = Index("ix_tasks_cluster_id", Task.cluster_id)
ix_threads_task_id_status = Index(
    "ix_threads_task_id_status",
    Thread.task_id,
    Thread.status,
)
ix_clusters_owner_id = Index("ix_clusters_owner_id", Cluster.owner_id)
ix_clusters_org_id_cluster_type = Index(
    "ix_clusters_org_id_cluster_type",
    Cluster.org_id,
    Cluster.cluster_type,
)

# Section 9.3 — Document pipeline
ix_kb_documents_status = Index("ix_kb_documents_status", KBDocument.status)
ix_kb_documents_collection_id_is_active = Index(
    "ix_kb_documents_collection_id_is_active",
    KBDocument.collection_id,
    KBDocument.is_active,
)
ix_kb_documents_collection_id_active_deleted = Index(
    "ix_kb_documents_collection_id_active_deleted",
    KBDocument.collection_id,
    KBDocument.is_active,
    KBDocument.is_deleted,
)
ix_kb_collections_owner_id = Index("ix_kb_collections_owner_id", KBCollection.owner_id)

# Section 9.4 — Workflow engine
ix_workflow_executions_task_id_status = Index(
    "ix_workflow_executions_task_id_status",
    WorkflowExecution.task_id,
    WorkflowExecution.status,
)
ix_workflow_thread_executions_workflow_execution_id_status = Index(
    "ix_workflow_thread_executions_workflow_execution_id_status",
    WorkflowThreadExecution.workflow_execution_id,
    WorkflowThreadExecution.status,
)
ix_workflow_interventions_workflow_execution_id = Index(
    "ix_workflow_interventions_workflow_execution_id",
    WorkflowIntervention.workflow_execution_id,
)

ix_user_invitations_org_id = Index(
    "ix_user_invitations_org_id",
    UserInvitation.org_id,
)
ix_user_invitations_email = Index(
    "ix_user_invitations_email",
    UserInvitation.email,
)

# HNSW index (ix_document_chunks_embedding_hnsw) is created via raw SQL in Alembic only.
