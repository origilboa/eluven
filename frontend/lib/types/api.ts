/** API response types aligned with backend data model Section 10.x schemas. */

export type UserResponse = {
  id: string;
  email: string;
  name: string;
  role: string;
  org_id: string;
  default_working_language: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: UserResponse;
};

export type RefreshResponse = {
  access_token: string;
  token_type: string;
  refresh_token: string;
};

export type TaskResponse = {
  id: string;
  title: string;
  module_type: string;
  status: string;
  cluster_id: string | null;
  working_language: string | null;
  context: Record<string, unknown> | null;
  structured_tags: Record<string, unknown> | null;
  freeform_tags: string[] | null;
  thread_count: number;
  created_at: string;
  updated_at: string;
};

export type CreateTaskRequest = {
  title: string;
  module_type: string;
  cluster_id?: string | null;
  working_language?: string | null;
  context?: Record<string, unknown> | null;
  structured_tags?: Record<string, unknown> | null;
  freeform_tags?: string[] | null;
};

export type TaskMemoryEntryResponse = {
  id: string;
  entry_type: string;
  content: string;
  confidence: number | null;
  thread_id: string;
  model_id: string | null;
  is_automated: boolean;
  created_at: string;
};

export type TaskMemoryResponse = {
  findings: TaskMemoryEntryResponse[];
  assumptions: TaskMemoryEntryResponse[];
  gaps: TaskMemoryEntryResponse[];
  references: TaskMemoryEntryResponse[];
};

export type ClusterResponse = {
  id: string;
  name: string;
  cluster_type: string;
  description: string | null;
  working_language: string | null;
  structured_tags: Record<string, unknown> | null;
  freeform_tags: string[] | null;
  task_count: number;
  created_at: string;
};

export type CreateClusterRequest = {
  name: string;
  cluster_type: string;
  description?: string | null;
  working_language?: string | null;
  structured_tags?: Record<string, unknown> | null;
  freeform_tags?: string[] | null;
};

export type CreateThreadRequest = {
  thread_type: string;
  title?: string | null;
  working_language?: string | null;
};

export type ActivityLibraryEntryResponse = {
  id: string;
  thread_type: string;
  module_type: string;
  display_name: string;
  description: string | null;
  scope: string;
  default_model_id: string;
  token_budget: number | null;
  supports_automation: boolean;
};

export type StreamStatusEvent = {
  type: "status";
  message: string;
};

export type StreamTextEvent = {
  type: "text";
  text: string;
};

export type StreamMemoryEntryEvent = {
  type: "memory_entry";
  entry: TaskMemoryEntryResponse;
};

export type StreamDoneEvent = {
  type: "done";
  input_tokens: number;
  output_tokens: number;
  cached_tokens?: number;
};

export type StreamErrorEvent = {
  type: "error";
  message: string;
};

export type StreamEvent =
  | StreamStatusEvent
  | StreamTextEvent
  | StreamMemoryEntryEvent
  | StreamDoneEvent
  | StreamErrorEvent;

export type ThreadResponse = {
  id: string;
  task_id: string;
  title: string;
  thread_type: string;
  status: string;
  working_language: string | null;
  is_automated: boolean;
  token_budget: number | null;
  tokens_used: number;
  created_at: string;
};

export type MessageResponse = {
  id: string;
  role: string;
  content: string;
  is_compaction_summary: boolean;
  input_tokens: number | null;
  output_tokens: number | null;
  cached_tokens: number | null;
  model_id: string | null;
  created_at: string;
};

export type ThreadDocumentResponse = {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
  load_strategy: string;
  token_count: number | null;
  created_at: string;
};

export type IntegrityFinding = {
  finding_type: string;
  count: number;
  detail: string | null;
};

export type IntegrityReportSummary = {
  status: "clean" | "warning" | "review_required";
  findings: IntegrityFinding[];
  content_hash: string | null;
  acknowledged: boolean;
  acknowledged_at: string | null;
};

export type TaskDocumentResponse = ThreadDocumentResponse & {
  integrity: IntegrityReportSummary | null;
};

export type TaskThreadDocumentResponse = ThreadDocumentResponse & {
  thread_id: string;
  thread_title: string;
  thread_type: string;
};

export type DocumentDownloadUrlResponse = {
  url: string;
  filename: string;
  expires_in_seconds: number;
};

export type TaskReferenceCollectionResponse = {
  id: string;
  attachment_id: string;
  name: string;
  description: string | null;
  document_count: number;
  attached_via: "task" | "cluster";
  created_at: string;
};

export type ClusterReferenceCollectionResponse = {
  id: string;
  attachment_id: string;
  name: string;
  description: string | null;
  document_count: number;
  created_at: string;
};

export type ThreadPromptResponse = {
  id: string;
  prompt_text: string;
  stage: string;
  sequence_index: number;
  used_at: string | null;
};

export type WorkflowTemplateResponse = {
  id: string;
  name: string;
  description: string | null;
  module_type: string;
  scope: string;
  thread_sequence: string[];
  created_at: string;
};

export type StartWorkflowRequest = {
  template_id: string;
};

export type CreateSubmissionRequest = {
  title: string;
  working_language?: string | null;
  context?: Record<string, unknown> | null;
  structured_tags?: Record<string, unknown> | null;
  freeform_tags?: string[] | null;
};

export type WorkflowThreadExecutionResponse = {
  id: string;
  thread_type: string;
  sequence_index: number;
  status: string;
  thread_id: string | null;
  retry_count: number;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export type WorkflowInterventionResponse = {
  id: string;
  workflow_thread_execution_id: string;
  trigger_type: string;
  question: string;
  user_response: string | null;
  triggered_at: string;
  responded_at: string | null;
};

export type WorkflowExecutionResponse = {
  id: string;
  task_id: string;
  status: string;
  current_thread_index: number;
  total_threads: number;
  total_tokens_used: number;
  thread_executions: WorkflowThreadExecutionResponse[];
  interventions: WorkflowInterventionResponse[];
  started_at: string;
  completed_at: string | null;
};

export type ApiErrorBody = {
  detail?: string | { msg: string }[];
};

export type KBAttachmentResponse = {
  id: string;
  entity_type: string;
  entity_id: string;
  entity_name: string;
  attached_at: string;
};

export type KBCollectionResponse = {
  id: string;
  name: string;
  description: string | null;
  document_count: number;
  attachments: KBAttachmentResponse[];
  created_at: string;
};

export type CreateCollectionRequest = {
  name: string;
  description?: string | null;
};

export type UpdateCollectionRequest = {
  name: string;
  description?: string | null;
};

export type AttachCollectionRequest = {
  entity_type: "task" | "cluster";
  entity_id: string;
};

export type KBDocumentResponse = {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
  chunk_count: number;
  version: number;
  integrity: IntegrityReportSummary | null;
  created_at: string;
};

export type TaskIntegrityDocumentSummary = {
  document_id: string;
  filename: string;
  source: string;
  integrity_status: "clean" | "warning" | "review_required";
  findings: IntegrityFinding[];
};

export type TaskIntegrityGateResponse = {
  blocked: boolean;
  unacknowledged_documents: TaskIntegrityDocumentSummary[];
};

export type AcknowledgeIntegrityRequest = {
  choice: "proceed" | "cancel";
};

export type InstructionVersionResponse = {
  id: string;
  version_number: number;
  content: string;
  change_note: string | null;
  created_by: string;
  created_at: string;
  is_active: boolean;
};

export type InstructionSetResponse = {
  id: string;
  level: string;
  thread_type?: string | null;
  cluster_id?: string | null;
  task_id?: string | null;
  thread_id?: string | null;
  active_version: InstructionVersionResponse | null;
  versions: InstructionVersionResponse[];
};

export type CreateInstructionVersionRequest = {
  content: string;
  change_note?: string | null;
};

export type ActivateInstructionVersionRequest = {
  version_id: string;
};

export type InstructionLevel = "platform" | "org" | "user";

export type InstructionAuthoringTarget = "instruction_set" | "activity_library_default";

export type ActivityDraftMetadata = {
  display_name?: string | null;
  description?: string | null;
  thread_type?: string | null;
  module_type?: string | null;
  supports_automation?: boolean | null;
};

export type InstructionAssistantScope = {
  authoring_target: InstructionAuthoringTarget;
  level: InstructionLevel | "cluster" | "task" | "thread";
  cluster_id?: string;
  task_id?: string;
  thread_id?: string;
  thread_type?: string | null;
  module_type?: string | null;
  activity_entry_id?: string;
  activity_draft?: ActivityDraftMetadata | null;
};

export type PromptAuthoringMode = "create" | "edit";

export type PromptAssistantScope = {
  authoring_mode: PromptAuthoringMode;
  level: "platform" | "org";
  activity_entry_id?: string;
  thread_type?: string | null;
  module_type?: string | null;
  activity_draft?: ActivityDraftMetadata | null;
  supports_automation?: boolean | null;
  default_instruction_content?: string | null;
};

export type ActivityPromptDraftItem = {
  prompt_text: string;
  stage: "opening" | "mid" | "closing";
  sequence_index: number;
};

export type PromptAssistantStreamRequest = {
  scope: PromptAssistantScope;
  draft_prompts: ActivityPromptDraftItem[];
  messages: { role: "user" | "assistant"; content: string }[];
  locale: "en" | "he";
};

export type ActivityAssistantStep =
  | "purpose"
  | "identity"
  | "mode"
  | "instructions"
  | "prompts"
  | "routing"
  | "review";

export type ActivityTypeDraft = {
  module_type?: string | null;
  purpose_notes?: string | null;
  thread_type?: string | null;
  display_name?: string | null;
  description?: string | null;
  supports_automation?: boolean | null;
  default_instruction_content?: string | null;
  prompts?: ActivityPromptDraftItem[];
  default_model_id?: string | null;
  fallback_model_id?: string | null;
  token_budget?: number | null;
  token_budget_warning_threshold?: number | null;
  model_routing_rationale?: string | null;
  scope_level?: "platform" | "org";
};

export type ActivityOrchestratorStreamRequest = {
  step: ActivityAssistantStep;
  draft: ActivityTypeDraft;
  messages: { role: "user" | "assistant"; content: string }[];
  locale: "en" | "he";
};

export type InstructionAssistantStreamRequest = {
  scope: InstructionAssistantScope;
  draft_content: string;
  messages: { role: "user" | "assistant"; content: string }[];
  locale: "en" | "he";
  integrity_review?: boolean;
};

export type AdminOrgResponse = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  user_count: number;
  is_platform_org: boolean;
  created_at: string;
};

export type CreateOrgRequest = {
  name: string;
  slug?: string | null;
};

export type UpdateOrgRequest = {
  name?: string | null;
  slug?: string | null;
  is_active?: boolean | null;
};

export type AdminUserResponse = {
  id: string;
  org_id: string;
  org_name: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  default_working_language: string;
  last_login_at: string | null;
  created_at: string;
};

export type UpdateAdminUserRequest = {
  name?: string | null;
  role?: string | null;
  default_working_language?: string | null;
  is_active?: boolean | null;
};

export type InvitationResponse = {
  id: string;
  org_id: string;
  org_name: string;
  email: string;
  name: string;
  role: string;
  status: string;
  invited_by_name: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
};

export type CreateInvitationRequest = {
  email: string;
  name: string;
  role: string;
  org_id?: string | null;
};

export type CreateInvitationResponse = {
  invitation: InvitationResponse;
  invite_url: string;
};

export type InvitationPreviewResponse = {
  email: string;
  name: string;
  org_name: string;
  role: string;
  expires_at: string;
  is_valid: boolean;
};

export type AcceptInviteRequest = {
  token: string;
  password: string;
};

export type AdminActivityPromptResponse = {
  id: string;
  prompt_text: string;
  stage: string;
  sequence_index: number;
};

export type AdminActivityLibraryEntryResponse = {
  id: string;
  thread_type: string;
  module_type: string;
  display_name: string;
  description: string | null;
  scope: string;
  is_active: boolean;
  default_model_id: string;
  fallback_model_id: string | null;
  token_budget: number | null;
  token_budget_warning_threshold: number;
  supports_automation: boolean;
  default_instruction_content: string | null;
  prompt_count: number;
  created_at: string;
  updated_at: string;
};

export type AdminActivityLibraryDetailResponse = AdminActivityLibraryEntryResponse & {
  prompts: AdminActivityPromptResponse[];
};

export type CreateActivityLibraryEntryRequest = {
  thread_type: string;
  module_type: string;
  display_name: string;
  description?: string | null;
  default_model_id?: string | null;
  fallback_model_id?: string | null;
  token_budget?: number | null;
  token_budget_warning_threshold?: number;
  supports_automation?: boolean;
  default_instruction_content?: string | null;
  is_active?: boolean;
};

export type UpdateActivityLibraryEntryRequest = {
  display_name?: string;
  description?: string | null;
  default_model_id?: string;
  fallback_model_id?: string | null;
  token_budget?: number | null;
  token_budget_warning_threshold?: number;
  supports_automation?: boolean;
  default_instruction_content?: string | null;
  is_active?: boolean;
};

export type UpsertActivityPromptRequest = {
  prompt_text: string;
};

export type ReplaceActivityPromptsRequest = {
  prompts: UpsertActivityPromptRequest[];
};
