"""Initial schema — all tables, indexes, pgvector, platform org seed.

Revision ID: 001
Revises:
Create Date: 2026-05-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None

# Reusable column bundles
_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")
_EMPTY_STR_ARRAY = sa.text("ARRAY[]::varchar[]")
_EMPTY_UUID_ARRAY = sa.text("ARRAY[]::uuid[]")


def _created_updated() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    ]


def upgrade() -> None:
    """Create extension, all tables, indexes, HNSW, and platform org seed."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- Group 1: Org and User ---
    op.create_table(
        "orgs",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_created_updated(),
        sa.UniqueConstraint("slug", name="uq_orgs_slug"),
    )

    op.create_table(
        "users",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="user", nullable=False),
        sa.Column("default_working_language", sa.String(10), server_default="en", nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_created_updated(),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # --- Group 2: Cluster and Task ---
    op.create_table(
        "clusters",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("owner_id", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cluster_type", sa.String(100), nullable=False),
        sa.Column("working_language", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_created_updated(),
    )

    op.create_table(
        "task_templates",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("owner_id", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("module_type", sa.String(100), nullable=False),
        sa.Column("working_language", sa.String(10), nullable=True),
        sa.Column(
            "default_thread_types",
            postgresql.ARRAY(sa.String()),
            server_default=_EMPTY_STR_ARRAY,
            nullable=False,
        ),
        sa.Column(
            "default_collection_ids",
            postgresql.ARRAY(_UUID),
            server_default=_EMPTY_UUID_ARRAY,
            nullable=False,
        ),
        sa.Column("context_defaults", postgresql.JSONB(), nullable=True),
        *_created_updated(),
    )

    op.create_table(
        "tasks",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("owner_id", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cluster_id", _UUID, sa.ForeignKey("clusters.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="draft", nullable=False),
        sa.Column("working_language", sa.String(10), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        *_created_updated(),
    )

    # --- Group 5: Instruction Layer (before threads for FK on overrides) ---
    op.create_table(
        "instruction_sets",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("level", sa.String(50), nullable=False),
        sa.Column("thread_type", sa.String(100), nullable=True),
        sa.Column("active_version_id", _UUID, nullable=True),
        sa.Column("platform_id", _UUID, nullable=True),
        sa.Column("owner_org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=True),
        sa.Column("user_id", _UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cluster_id", _UUID, sa.ForeignKey("clusters.id"), nullable=True),
        sa.Column("task_id", _UUID, sa.ForeignKey("tasks.id"), nullable=True),
        *_created_updated(),
    )

    op.create_table(
        "instruction_versions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "instruction_set_id",
            _UUID,
            sa.ForeignKey("instruction_sets.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("change_note", sa.String(500), nullable=True),
        sa.Column("created_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    op.create_table(
        "task_thread_type_instructions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("task_id", _UUID, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("thread_type", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    # --- Group 3: Thread and ThreadMessage ---
    op.create_table(
        "threads",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("task_id", _UUID, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("owner_id", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("thread_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="draft", nullable=False),
        sa.Column("working_language", sa.String(10), nullable=True),
        sa.Column("is_automated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("instruction_version", sa.String(50), nullable=True),
        sa.Column("token_budget", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False),
        *_created_updated(),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "task_instruction_overrides",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("task_id", _UUID, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("thread_id", _UUID, sa.ForeignKey("threads.id"), nullable=True),
        sa.Column("overrides_level", sa.String(50), nullable=False),
        sa.Column("override_description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    op.create_table(
        "thread_messages",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("thread_id", _UUID, sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_compaction_summary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    # --- Group 4: TaskMemory ---
    op.create_table(
        "task_memory_entries",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("task_id", _UUID, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("thread_id", _UUID, sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("entry_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "source_chunk_ids",
            postgresql.ARRAY(sa.String()),
            server_default=_EMPTY_STR_ARRAY,
            nullable=False,
        ),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column("instruction_version", sa.String(50), nullable=True),
        sa.Column("is_automated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    # --- Group 6: KB ---
    op.create_table(
        "kb_collections",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("owner_id", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_org_collection", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_created_updated(),
    )

    op.create_table(
        "kb_collection_attachments",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("collection_id", _UUID, sa.ForeignKey("kb_collections.id"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", _UUID, nullable=False),
        sa.Column("attached_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    op.create_table(
        "kb_documents",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("collection_id", _UUID, sa.ForeignKey("kb_collections.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("previous_version_id", _UUID, sa.ForeignKey("kb_documents.id"), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("uploaded_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_created_updated(),
    )

    op.create_table(
        "thread_documents",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("thread_id", _UUID, sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("load_strategy", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("uploaded_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("collection_id", _UUID, sa.ForeignKey("kb_collections.id"), nullable=True),
        sa.Column("document_id", _UUID, sa.ForeignKey("kb_documents.id"), nullable=True),
        sa.Column("thread_document_id", _UUID, sa.ForeignKey("thread_documents.id"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    # --- Group 7: Workflow ---
    op.create_table(
        "workflow_templates",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("owner_id", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module_type", sa.String(100), nullable=False),
        sa.Column("scope", sa.String(50), nullable=False),
        sa.Column("thread_sequence", postgresql.ARRAY(sa.String()), nullable=False),
        *_created_updated(),
    )

    op.create_table(
        "workflow_executions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("task_id", _UUID, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("template_id", _UUID, sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("triggered_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(50), server_default="running", nullable=False),
        sa.Column("current_thread_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_threads", sa.Integer(), nullable=False),
        sa.Column("total_tokens_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "workflow_thread_executions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "workflow_execution_id",
            _UUID,
            sa.ForeignKey("workflow_executions.id"),
            nullable=False,
        ),
        sa.Column("thread_id", _UUID, sa.ForeignKey("threads.id"), nullable=True),
        sa.Column("thread_type", sa.String(100), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "workflow_interventions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "workflow_execution_id",
            _UUID,
            sa.ForeignKey("workflow_executions.id"),
            nullable=False,
        ),
        sa.Column(
            "workflow_thread_execution_id",
            _UUID,
            sa.ForeignKey("workflow_thread_executions.id"),
            nullable=False,
        ),
        sa.Column("trigger_type", sa.String(100), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("user_response", sa.Text(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Group 8: ActivityLibrary ---
    op.create_table(
        "activity_library_entries",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("thread_type", sa.String(100), nullable=False),
        sa.Column("module_type", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("default_model_id", sa.String(100), nullable=False),
        sa.Column("fallback_model_id", sa.String(100), nullable=True),
        sa.Column("model_routing_rationale", sa.Text(), nullable=True),
        sa.Column("token_budget", sa.Integer(), nullable=True),
        sa.Column(
            "token_budget_warning_threshold",
            sa.Float(),
            server_default="0.8",
            nullable=False,
        ),
        sa.Column("supports_automation", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("automation_execution_spec", postgresql.JSONB(), nullable=True),
        *_created_updated(),
    )

    op.create_table(
        "thread_qa_questions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "activity_entry_id",
            _UUID,
            sa.ForeignKey("activity_library_entries.id"),
            nullable=False,
        ),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("response_type", sa.String(50), server_default="text", nullable=False),
        sa.Column("options", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    op.create_table(
        "thread_qa_responses",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("thread_id", _UUID, sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("question_id", _UUID, sa.ForeignKey("thread_qa_questions.id"), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("response_options", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )

    # --- Section 9: Database indexes ---
    # 9.1 Critical path
    op.create_index(
        "ix_thread_messages_thread_id_created_at",
        "thread_messages",
        ["thread_id", "created_at"],
    )
    op.create_index("ix_task_memory_entries_task_id", "task_memory_entries", ["task_id"])
    op.create_index(
        "ix_task_memory_entries_task_id_type",
        "task_memory_entries",
        ["task_id", "entry_type"],
    )
    op.create_index(
        "ix_document_chunks_org_id_collection_id",
        "document_chunks",
        ["org_id", "collection_id"],
    )
    op.create_index(
        "ix_document_chunks_thread_document_id",
        "document_chunks",
        ["thread_document_id"],
    )
    op.create_index(
        "ix_kb_collection_attachments_entity",
        "kb_collection_attachments",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_kb_collections_org_id_is_org_collection",
        "kb_collections",
        ["org_id", "is_org_collection"],
    )
    op.create_index("ix_instruction_sets_task_id", "instruction_sets", ["task_id"])
    op.create_index("ix_instruction_sets_cluster_id", "instruction_sets", ["cluster_id"])
    op.create_index("ix_instruction_sets_user_id", "instruction_sets", ["user_id"])
    op.create_index("ix_instruction_sets_org_id", "instruction_sets", ["owner_org_id"])
    op.create_index(
        "ix_task_thread_type_instructions_task_id_thread_type",
        "task_thread_type_instructions",
        ["task_id", "thread_type"],
    )
    op.create_index("ix_thread_qa_responses_thread_id", "thread_qa_responses", ["thread_id"])

    # 9.2 Dashboard and navigation
    op.create_index("ix_tasks_owner_id_status", "tasks", ["owner_id", "status"])
    op.create_index("ix_tasks_cluster_id", "tasks", ["cluster_id"])
    op.create_index("ix_threads_task_id_status", "threads", ["task_id", "status"])
    op.create_index("ix_clusters_owner_id", "clusters", ["owner_id"])
    op.create_index("ix_clusters_org_id_cluster_type", "clusters", ["org_id", "cluster_type"])

    # 9.3 Document pipeline
    op.create_index("ix_kb_documents_status", "kb_documents", ["status"])
    op.create_index(
        "ix_kb_documents_collection_id_is_active",
        "kb_documents",
        ["collection_id", "is_active"],
    )
    op.create_index(
        "ix_kb_documents_collection_id_active_deleted",
        "kb_documents",
        ["collection_id", "is_active", "is_deleted"],
    )
    op.create_index("ix_kb_collections_owner_id", "kb_collections", ["owner_id"])

    # 9.4 Workflow engine
    op.create_index(
        "ix_workflow_executions_task_id_status",
        "workflow_executions",
        ["task_id", "status"],
    )
    op.create_index(
        "ix_workflow_thread_executions_workflow_execution_id_status",
        "workflow_thread_executions",
        ["workflow_execution_id", "status"],
    )
    op.create_index(
        "ix_workflow_interventions_workflow_execution_id",
        "workflow_interventions",
        ["workflow_execution_id"],
    )

    # 9.5 pgvector HNSW index (raw SQL per data model spec)
    op.execute(
        """
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # Platform org seed (Section 11)
    op.execute(
        """
        INSERT INTO orgs (id, name, slug, is_active, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            'Eluven',
            'eluven',
            true,
            now(),
            now()
        )
        """
    )

    # ActivityLibrary entries added here per thread type.
    # See /docs/instructions/ for master instruction content.


def downgrade() -> None:
    """Drop HNSW index, all tables, and pgvector extension."""
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")

    tables: Sequence[str] = (
        "thread_qa_responses",
        "thread_qa_questions",
        "activity_library_entries",
        "workflow_interventions",
        "workflow_thread_executions",
        "workflow_executions",
        "workflow_templates",
        "document_chunks",
        "thread_documents",
        "kb_documents",
        "kb_collection_attachments",
        "kb_collections",
        "task_memory_entries",
        "thread_messages",
        "task_instruction_overrides",
        "threads",
        "task_thread_type_instructions",
        "instruction_versions",
        "instruction_sets",
        "tasks",
        "task_templates",
        "clusters",
        "users",
        "orgs",
    )
    for table in tables:
        op.drop_table(table)

    op.execute("DROP EXTENSION IF EXISTS vector")
