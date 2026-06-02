"""Rich demo dataset for manual MVP testing — three roles, tasks, threads, KB, workflows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.security import hash_password
from models.activity import ActivityLibraryEntry, QAStage, ThreadQAQuestion, ThreadQAResponse
from models.cluster import Cluster
from models.invitation import UserInvitation
from models.kb import KBCollection, KBCollectionAttachment
from models.memory import TaskMemoryEntry, TaskMemoryEntryType
from models.org import Org
from models.task import Task, TaskStatus
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
from seed.constants import (
    DEMO_INVITATION_TOKEN,
    DEMO_INVITEE_EMAIL,
    DEMO_INVITEE_NAME,
    DEMO_ORG_B_NAME,
    DEMO_ORG_B_SLUG,
    DEV_ORG_NAME,
    DEV_ORG_SLUG,
    DEV_USER_EMAIL,
    DEV_USER_NAME,
    DEV_USER_PASSWORD,
    MVP_MODULE_EPR,
    MVP_MODULE_SPR,
    ORG_ADMIN_USER_EMAIL,
    ORG_ADMIN_USER_NAME,
    ORG_ADMIN_USER_PASSWORD,
    REVIEWER_USER_EMAIL,
    REVIEWER_USER_NAME,
    REVIEWER_USER_PASSWORD,
    TEMPLATE_EPR_FULL_ID,
    TEMPLATE_SPR_FULL_ID,
)
from seed.documents import (
    purge_dev_org_s3_prefix,
    seed_kb_document_processed,
    seed_task_document,
)
from services.invitations import hash_invite_token, invitation_expires_at

logger = get_logger(__name__)

_DEMO_MARKER = "Demo "


async def seed_demo_async(session: AsyncSession) -> None:
    """Seed idempotent demo data for three roles with varied tasks and flows."""
    org = await _get_or_create_org(session, name=DEV_ORG_NAME, slug=DEV_ORG_SLUG)
    purge_dev_org_s3_prefix(org.id)

    await _get_or_create_org(session, name=DEMO_ORG_B_NAME, slug=DEMO_ORG_B_SLUG)

    dev_user = await _get_or_create_user(
        session,
        org=org,
        email=DEV_USER_EMAIL,
        name=DEV_USER_NAME,
        role=UserRole.APP_ADMIN,
        password=DEV_USER_PASSWORD,
    )
    org_admin = await _get_or_create_user(
        session,
        org=org,
        email=ORG_ADMIN_USER_EMAIL,
        name=ORG_ADMIN_USER_NAME,
        role=UserRole.ORG_ADMIN,
        password=ORG_ADMIN_USER_PASSWORD,
    )
    reviewer = await _get_or_create_user(
        session,
        org=org,
        email=REVIEWER_USER_EMAIL,
        name=REVIEWER_USER_NAME,
        role=UserRole.USER,
        password=REVIEWER_USER_PASSWORD,
    )

    epr_draft = await _get_or_create_task(
        session,
        org=org,
        owner=dev_user,
        title=f"{_DEMO_MARKER}EPR — Draft (empty)",
        module_type=MVP_MODULE_EPR,
        status=TaskStatus.DRAFT,
        description="Empty draft task for testing task creation and first upload flows.",
    )

    epr_active = await _get_or_create_task(
        session,
        org=org,
        owner=dev_user,
        title=f"{_DEMO_MARKER}EPR — Methods paper (in progress)",
        module_type=MVP_MODULE_EPR,
        status=TaskStatus.ACTIVE,
        description="Active review with threads, task memory, and attached KB collection.",
    )

    epr_hebrew = await _get_or_create_task(
        session,
        org=org,
        owner=dev_user,
        title=f"{_DEMO_MARKER}EPR — Hebrew locale",
        module_type=MVP_MODULE_EPR,
        status=TaskStatus.ACTIVE,
        working_language="he",
        description="Task with working_language=he for RTL validation.",
    )

    epr_workflow = await _get_or_create_task(
        session,
        org=org,
        owner=dev_user,
        title=f"{_DEMO_MARKER}EPR — Workflow paused (intervention)",
        module_type=MVP_MODULE_EPR,
        status=TaskStatus.ACTIVE,
        description="Workflow execution paused on an intervention trigger for UI testing.",
    )

    await _get_or_create_task(
        session,
        org=org,
        owner=reviewer,
        title=f"{_DEMO_MARKER}EPR — Reviewer-owned journal paper",
        module_type=MVP_MODULE_EPR,
        status=TaskStatus.ACTIVE,
        description="Owned by the second user to verify per-user task lists.",
    )

    assignment = await _get_or_create_cluster(
        session,
        org=org,
        owner=dev_user,
        name=f"{_DEMO_MARKER}Assignment — Research Methods 101",
        cluster_type="assignment",
        description="Sample assignment with two student submissions.",
    )

    spr_alice = await _get_or_create_task(
        session,
        org=org,
        owner=dev_user,
        title=f"{_DEMO_MARKER}SPR — Alice Chen submission",
        module_type=MVP_MODULE_SPR,
        status=TaskStatus.ACTIVE,
        cluster_id=assignment.id,
        description="In-progress student submission with an active evaluation thread.",
    )

    await _get_or_create_task(
        session,
        org=org,
        owner=dev_user,
        title=f"{_DEMO_MARKER}SPR — Bob Martinez submission",
        module_type=MVP_MODULE_SPR,
        status=TaskStatus.DRAFT,
        cluster_id=assignment.id,
        description="Draft submission — not yet reviewed.",
    )

    spr_workflow = await _get_or_create_task(
        session,
        org=org,
        owner=dev_user,
        title=f"{_DEMO_MARKER}SPR — Workflow paused (intervention)",
        module_type=MVP_MODULE_SPR,
        status=TaskStatus.ACTIVE,
        cluster_id=assignment.id,
        description="SPR workflow paused on an intervention trigger for UI testing.",
    )

    await _seed_epr_threads_and_memory(session, org=org, owner=dev_user, task=epr_active)
    initial_read = await session.execute(
        select(Thread).where(
            Thread.task_id == epr_active.id,
            Thread.thread_type == "initial_read",
        ),
    )
    initial_read_thread = initial_read.scalar_one_or_none()
    if initial_read_thread is not None:
        await _seed_opening_qa_responses(session, thread=initial_read_thread)

    await _seed_spr_thread(session, org=org, owner=dev_user, task=spr_alice)
    kb_collection = await _seed_kb_collection(
        session,
        org=org,
        owner=dev_user,
        task=epr_active,
        cluster=assignment,
    )
    await seed_task_document(
        session,
        org=org,
        task=epr_active,
        owner=dev_user,
        filename="demo-manuscript.pdf",
        fixture_name="sample.pdf",
    )
    await seed_task_document(
        session,
        org=org,
        task=spr_alice,
        owner=dev_user,
        filename="demo-submission.pdf",
        fixture_name="sample.pdf",
    )
    await _seed_paused_workflow(
        session,
        org=org,
        owner=dev_user,
        task=epr_workflow,
        template_id=UUID(TEMPLATE_EPR_FULL_ID),
        intervention_question=(
            "The paper describes two competing operational definitions of 'engagement'. "
            "Which definition should be used for the methodology assessment?"
        ),
    )
    await _seed_paused_workflow(
        session,
        org=org,
        owner=dev_user,
        task=spr_workflow,
        template_id=UUID(TEMPLATE_SPR_FULL_ID),
        intervention_question=(
            "The rubric scores 'literature review' on sources from 2015–2020, but the essay "
            "mostly cites 2022–2024 papers. Which criterion should govern this section?"
        ),
    )
    await _seed_pending_invitation(session, org=org, invited_by=org_admin)

    from seed.instructions import seed_sample_instructions_for_session

    instructions_seeded = await seed_sample_instructions_for_session(session)

    await session.commit()

    logger.info(
        "seed_demo_complete",
        org_slug=DEV_ORG_SLUG,
        dev_user=DEV_USER_EMAIL,
        org_admin_user=ORG_ADMIN_USER_EMAIL,
        reviewer_user=REVIEWER_USER_EMAIL,
        task_count=8,
        cluster_id=str(assignment.id),
        epr_draft_id=str(epr_draft.id),
        epr_active_id=str(epr_active.id),
        kb_collection_id=str(kb_collection.id) if kb_collection else None,
        demo_invitation_token=DEMO_INVITATION_TOKEN,
        instructions_seeded=instructions_seeded,
    )


async def _get_or_create_org(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
) -> Org:
    result = await session.execute(select(Org).where(Org.slug == slug))
    org = result.scalar_one_or_none()
    if org is not None:
        return org

    org = Org(name=name, slug=slug)
    session.add(org)
    await session.flush()
    logger.info("seed_demo_org_created", slug=slug)
    return org


async def _get_or_create_user(
    session: AsyncSession,
    *,
    org: Org,
    email: str,
    name: str,
    role: UserRole,
    password: str,
) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        org_id=org.id,
        email=email,
        name=name,
        role=role,
        hashed_password=hash_password(password),
    )
    session.add(user)
    await session.flush()
    logger.info("seed_demo_user_created", email=email, role=role.value)
    return user


async def _get_or_create_task(
    session: AsyncSession,
    *,
    org: Org,
    owner: User,
    title: str,
    module_type: str,
    status: TaskStatus,
    description: str | None = None,
    working_language: str | None = None,
    cluster_id: UUID | None = None,
) -> Task:
    result = await session.execute(
        select(Task).where(Task.owner_id == owner.id, Task.title == title),
    )
    task = result.scalar_one_or_none()
    if task is not None:
        return task

    task = Task(
        org_id=org.id,
        owner_id=owner.id,
        cluster_id=cluster_id,
        title=title,
        description=description,
        module_type=module_type,
        status=status,
        working_language=working_language,
    )
    session.add(task)
    await session.flush()
    logger.info("seed_demo_task_created", title=title, task_id=str(task.id))
    return task


async def _get_or_create_cluster(
    session: AsyncSession,
    *,
    org: Org,
    owner: User,
    name: str,
    cluster_type: str,
    description: str | None = None,
) -> Cluster:
    result = await session.execute(
        select(Cluster).where(Cluster.owner_id == owner.id, Cluster.name == name),
    )
    cluster = result.scalar_one_or_none()
    if cluster is not None:
        return cluster

    cluster = Cluster(
        org_id=org.id,
        owner_id=owner.id,
        name=name,
        description=description,
        cluster_type=cluster_type,
    )
    session.add(cluster)
    await session.flush()
    logger.info("seed_demo_cluster_created", name=name, cluster_id=str(cluster.id))
    return cluster


async def _get_or_create_thread(
    session: AsyncSession,
    *,
    org: Org,
    task: Task,
    owner: User,
    thread_type: str,
    title: str,
    status: ThreadStatus,
) -> Thread:
    result = await session.execute(
        select(Thread).where(
            Thread.task_id == task.id,
            Thread.thread_type == thread_type,
        ),
    )
    thread = result.scalar_one_or_none()
    if thread is not None:
        return thread

    thread = Thread(
        org_id=org.id,
        task_id=task.id,
        owner_id=owner.id,
        title=title,
        thread_type=thread_type,
        status=status,
        working_language=task.working_language,
    )
    session.add(thread)
    await session.flush()
    logger.info(
        "seed_demo_thread_created",
        thread_type=thread_type,
        thread_id=str(thread.id),
        task_id=str(task.id),
    )
    return thread


async def _seed_thread_messages_if_empty(
    session: AsyncSession,
    thread: Thread,
    exchanges: list[tuple[str, str]],
) -> None:
    result = await session.execute(
        select(ThreadMessage.id).where(ThreadMessage.thread_id == thread.id).limit(1),
    )
    if result.scalar_one_or_none() is not None:
        return

    for user_text, assistant_text in exchanges:
        session.add(
            ThreadMessage(
                thread_id=thread.id,
                role=MessageRole.USER,
                content=user_text,
            ),
        )
        session.add(
            ThreadMessage(
                thread_id=thread.id,
                role=MessageRole.ASSISTANT,
                content=assistant_text,
                model_id="seed/demo",
            ),
        )
    await session.flush()


async def _seed_epr_threads_and_memory(
    session: AsyncSession,
    *,
    org: Org,
    owner: User,
    task: Task,
) -> None:
    initial_read = await _get_or_create_thread(
        session,
        org=org,
        task=task,
        owner=owner,
        thread_type="initial_read",
        title="Initial Read",
        status=ThreadStatus.COMPLETE,
    )
    await _seed_thread_messages_if_empty(
        session,
        initial_read,
        [
            (
                "Summarize the paper's main contribution and research question.",
                (
                    "The paper proposes a mixed-methods evaluation of collaborative filtering "
                    "in academic recommender systems. The central research question asks whether "
                    "hybrid approaches outperform pure content-based methods for research paper discovery."
                ),
            ),
        ],
    )

    methodology = await _get_or_create_thread(
        session,
        org=org,
        task=task,
        owner=owner,
        thread_type="methodology_review",
        title="Methodology Review",
        status=ThreadStatus.ACTIVE,
    )
    await _seed_thread_messages_if_empty(
        session,
        methodology,
        [
            (
                "Evaluate the study design and sample size justification.",
                (
                    "The study uses a within-subjects design with 48 participants from two "
                    "universities. Sample size is justified via power analysis (d=0.5, power=0.8), "
                    "though the participant pool may limit generalizability."
                ),
            ),
        ],
    )

    memory_specs: list[tuple[TaskMemoryEntryType, str, float, UUID]] = [
        (
            TaskMemoryEntryType.FINDING,
            "Power analysis supports n=48 for the primary comparison.",
            0.88,
            initial_read.id,
        ),
        (
            TaskMemoryEntryType.FINDING,
            "Hybrid recommender outperforms baseline on precision@10.",
            0.82,
            methodology.id,
        ),
        (
            TaskMemoryEntryType.ASSUMPTION,
            "Participants are familiar with academic search tools.",
            0.65,
            initial_read.id,
        ),
        (
            TaskMemoryEntryType.GAP,
            "No comparison with recent graph-based recommender baselines.",
            0.91,
            methodology.id,
        ),
        (
            TaskMemoryEntryType.REFERENCE,
            "Smith et al. (2024) — baseline content-based method cited in Section 2.",
            0.95,
            initial_read.id,
        ),
    ]

    for entry_type, content, confidence, thread_id in memory_specs:
        existing = await session.execute(
            select(TaskMemoryEntry.id).where(
                TaskMemoryEntry.task_id == task.id,
                TaskMemoryEntry.content == content,
            ),
        )
        if existing.scalar_one_or_none() is not None:
            continue

        session.add(
            TaskMemoryEntry(
                org_id=org.id,
                task_id=task.id,
                thread_id=thread_id,
                entry_type=entry_type,
                content=content,
                confidence=confidence,
                is_automated=False,
            ),
        )

    await session.flush()


async def _seed_spr_thread(
    session: AsyncSession,
    *,
    org: Org,
    owner: User,
    task: Task,
) -> None:
    submission_read = await _get_or_create_thread(
        session,
        org=org,
        task=task,
        owner=owner,
        thread_type="submission_read",
        title="Submission Read",
        status=ThreadStatus.ACTIVE,
    )
    await _seed_thread_messages_if_empty(
        session,
        submission_read,
        [
            (
                "Summarize the student's argument and thesis statement.",
                (
                    "The essay argues that peer review in undergraduate courses improves writing "
                    "quality when structured rubrics are used. The thesis is clearly stated in "
                    "the introduction but supporting evidence is uneven across sections."
                ),
            ),
        ],
    )

    existing = await session.execute(
        select(TaskMemoryEntry.id).where(
            TaskMemoryEntry.task_id == task.id,
            TaskMemoryEntry.content.like("Thesis is clearly stated%"),
        ),
    )
    if existing.scalar_one_or_none() is None:
        session.add(
            TaskMemoryEntry(
                org_id=org.id,
                task_id=task.id,
                thread_id=submission_read.id,
                entry_type=TaskMemoryEntryType.FINDING,
                content="Thesis is clearly stated; literature review section needs stronger citations.",
                confidence=0.84,
            ),
        )
        await session.flush()


async def _ensure_kb_attachment(
    session: AsyncSession,
    *,
    collection_id: UUID,
    entity_type: str,
    entity_id: UUID,
    attached_by: UUID,
) -> None:
    attachment_result = await session.execute(
        select(KBCollectionAttachment).where(
            KBCollectionAttachment.collection_id == collection_id,
            KBCollectionAttachment.entity_type == entity_type,
            KBCollectionAttachment.entity_id == entity_id,
        ),
    )
    if attachment_result.scalar_one_or_none() is None:
        session.add(
            KBCollectionAttachment(
                collection_id=collection_id,
                entity_type=entity_type,
                entity_id=entity_id,
                attached_by=attached_by,
            ),
        )


async def _seed_kb_collection(
    session: AsyncSession,
    *,
    org: Org,
    owner: User,
    task: Task,
    cluster: Cluster,
) -> KBCollection:
    collection_name = f"{_DEMO_MARKER}Reference — methodology guides"
    result = await session.execute(
        select(KBCollection).where(
            KBCollection.owner_id == owner.id,
            KBCollection.name == collection_name,
        ),
    )
    collection = result.scalar_one_or_none()
    if collection is None:
        collection = KBCollection(
            org_id=org.id,
            owner_id=owner.id,
            name=collection_name,
            description="Sample KB collection attached to the in-progress EPR demo task.",
        )
        session.add(collection)
        await session.flush()
        logger.info("seed_demo_kb_collection_created", collection_id=str(collection.id))

    await _ensure_kb_attachment(
        session,
        collection_id=collection.id,
        entity_type="task",
        entity_id=task.id,
        attached_by=owner.id,
    )
    await _ensure_kb_attachment(
        session,
        collection_id=collection.id,
        entity_type="cluster",
        entity_id=cluster.id,
        attached_by=owner.id,
    )

    await seed_kb_document_processed(
        session,
        org=org,
        collection_id=collection.id,
        owner=owner,
        filename="methods-guide.txt",
        fixture_name="sample.txt",
    )
    await session.flush()
    return collection


async def _seed_opening_qa_responses(
    session: AsyncSession,
    *,
    thread: Thread,
) -> None:
    task = await session.get(Task, thread.task_id)
    if task is None:
        return

    questions_result = await session.execute(
        select(ThreadQAQuestion)
        .join(
            ActivityLibraryEntry,
            ThreadQAQuestion.activity_entry_id == ActivityLibraryEntry.id,
        )
        .where(
            ActivityLibraryEntry.thread_type == thread.thread_type,
            ActivityLibraryEntry.module_type == task.module_type,
            ThreadQAQuestion.stage == QAStage.OPENING,
        )
        .order_by(ThreadQAQuestion.sequence_index.asc())
        .limit(1),
    )
    question = questions_result.scalar_one_or_none()
    if question is None:
        return

    existing = await session.execute(
        select(ThreadQAResponse.id).where(
            ThreadQAResponse.thread_id == thread.id,
            ThreadQAResponse.question_id == question.id,
        ),
    )
    if existing.scalar_one_or_none() is not None:
        return

    session.add(
        ThreadQAResponse(
            thread_id=thread.id,
            question_id=question.id,
            response_text=(
                "Proceed with a standard external review. Focus on methods validity first, "
                "then contribution and clarity."
            ),
        ),
    )
    await session.flush()
    logger.info("seed_demo_qa_response_created", thread_id=str(thread.id))


async def _seed_pending_invitation(
    session: AsyncSession,
    *,
    org: Org,
    invited_by: User,
) -> None:
    result = await session.execute(
        select(UserInvitation).where(
            UserInvitation.org_id == org.id,
            UserInvitation.email == DEMO_INVITEE_EMAIL.lower(),
            UserInvitation.accepted_at.is_(None),
            UserInvitation.revoked_at.is_(None),
        ),
    )
    if result.scalar_one_or_none() is not None:
        return

    session.add(
        UserInvitation(
            org_id=org.id,
            email=DEMO_INVITEE_EMAIL.lower(),
            name=DEMO_INVITEE_NAME,
            role=UserRole.USER,
            token_hash=hash_invite_token(DEMO_INVITATION_TOKEN),
            invited_by=invited_by.id,
            expires_at=invitation_expires_at(),
        ),
    )
    await session.flush()
    logger.info(
        "seed_demo_invitation_created",
        email=DEMO_INVITEE_EMAIL,
        invited_by=str(invited_by.id),
    )


async def _seed_paused_workflow(
    session: AsyncSession,
    *,
    org: Org,
    owner: User,
    task: Task,
    template_id: UUID,
    intervention_question: str,
) -> None:
    result = await session.execute(
        select(WorkflowExecution).where(WorkflowExecution.task_id == task.id),
    )
    if result.scalar_one_or_none() is not None:
        return

    template = await session.get(WorkflowTemplate, template_id)
    if template is None or len(template.thread_sequence) < 2:
        logger.warning(
            "seed_demo_workflow_skipped",
            reason="workflow_template_missing",
            template_id=str(template_id),
        )
        return

    first_type = template.thread_sequence[0]
    second_type = template.thread_sequence[1]

    initial_thread = await _get_or_create_thread(
        session,
        org=org,
        task=task,
        owner=owner,
        thread_type=first_type,
        title=f"{first_type.replace('_', ' ').title()} (workflow)",
        status=ThreadStatus.COMPLETE,
    )
    paused_thread = await _get_or_create_thread(
        session,
        org=org,
        task=task,
        owner=owner,
        thread_type=second_type,
        title=f"{second_type.replace('_', ' ').title()} (workflow)",
        status=ThreadStatus.ACTIVE,
    )

    execution = WorkflowExecution(
        org_id=org.id,
        task_id=task.id,
        template_id=template.id,
        triggered_by=owner.id,
        status=WorkflowStatus.PAUSED,
        current_thread_index=1,
        total_threads=len(template.thread_sequence),
        total_tokens_used=4200,
    )
    session.add(execution)
    await session.flush()

    step_rows: list[WorkflowThreadExecution] = []
    for index, thread_type in enumerate(template.thread_sequence):
        if index == 0:
            status = WorkflowThreadStatus.COMPLETE
            linked_thread_id = initial_thread.id
        elif index == 1:
            status = WorkflowThreadStatus.RUNNING
            linked_thread_id = paused_thread.id
        else:
            status = WorkflowThreadStatus.PENDING
            linked_thread_id = None

        step = WorkflowThreadExecution(
            workflow_execution_id=execution.id,
            thread_id=linked_thread_id,
            thread_type=thread_type,
            sequence_index=index,
            status=status,
        )
        step_rows.append(step)

    session.add_all(step_rows)
    await session.flush()

    paused_step = step_rows[1]
    session.add(
        WorkflowIntervention(
            workflow_execution_id=execution.id,
            workflow_thread_execution_id=paused_step.id,
            trigger_type=InterventionTriggerType.EXPLICIT_AMBIGUITY,
            question=intervention_question,
        ),
    )
    await session.flush()
    logger.info("seed_demo_workflow_created", workflow_id=str(execution.id), task_id=str(task.id))
