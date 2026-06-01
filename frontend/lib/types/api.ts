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
  task_count: number;
  created_at: string;
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

export type SubmitQARequest = {
  responses: QAResponseRequest[];
};

export type QAResponseRequest = {
  question_id: string;
  response_text?: string | null;
  response_options?: string[] | null;
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

export type QAQuestionResponse = {
  id: string;
  question_text: string;
  stage: string;
  response_type: string;
  options: string[] | null;
  is_required: boolean;
  sequence_index: number;
  response_text: string | null;
  response_options: string[] | null;
  responded_at: string | null;
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
