"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type {
  StartWorkflowRequest,
  WorkflowExecutionResponse,
  WorkflowTemplateResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type WorkflowPanelProps = {
  locale: Locale;
  taskId: string;
  moduleType: string;
};

export function WorkflowPanel({ locale, taskId, moduleType }: WorkflowPanelProps) {
  const queryClient = useQueryClient();
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [interventionResponse, setInterventionResponse] = useState("");
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "Workflow",
          start: "התחל workflow",
          starting: "מתחיל…",
          template: "תבנית",
          status: "סטטוס",
          noTemplates: "אין תבניות workflow זמינות למודול זה.",
          respond: "שלח תגובה",
          responding: "שולח…",
          pendingIntervention: "Workflow מושהה — נדרשת תגובה",
        }
      : {
          title: "Workflow",
          start: "Start workflow",
          starting: "Starting…",
          template: "Template",
          status: "Status",
          noTemplates: "No workflow templates available for this module.",
          respond: "Submit response",
          responding: "Submitting…",
          pendingIntervention: "Workflow paused — response required",
        };

  const templatesQuery = useQuery({
    queryKey: ["workflow-templates"],
    queryFn: () => api.get<WorkflowTemplateResponse[]>("/workflow-templates"),
  });

  const moduleTemplates =
    templatesQuery.data?.filter((template) => template.module_type === moduleType) ?? [];

  useEffect(() => {
    if (!selectedTemplateId && moduleTemplates.length > 0) {
      setSelectedTemplateId(moduleTemplates[0]?.id ?? "");
    }
  }, [moduleTemplates, selectedTemplateId]);

  const executionQuery = useQuery({
    queryKey: ["workflow-execution", taskId, activeExecutionId],
    queryFn: () =>
      api.get<WorkflowExecutionResponse>(`/tasks/${taskId}/workflows/${activeExecutionId}`),
    enabled: activeExecutionId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "running" || status === "paused") {
        return 3000;
      }
      return false;
    },
  });

  const startMutation = useMutation({
    mutationFn: (payload: StartWorkflowRequest) =>
      api.post<WorkflowExecutionResponse>(`/tasks/${taskId}/workflows`, payload),
    onSuccess: (execution) => {
      setActiveExecutionId(execution.id);
      void queryClient.invalidateQueries({ queryKey: ["workflow-execution", taskId] });
    },
  });

  const respondMutation = useMutation({
    mutationFn: ({
      executionId,
      interventionId,
      response,
    }: {
      executionId: string;
      interventionId: string;
      response: string;
    }) =>
      api.post<WorkflowExecutionResponse>(
        `/workflows/${executionId}/interventions/${interventionId}/respond`,
        { response },
      ),
    onSuccess: (execution) => {
      setInterventionResponse("");
      setActiveExecutionId(execution.id);
      void queryClient.invalidateQueries({
        queryKey: ["workflow-execution", taskId, execution.id],
      });
    },
  });

  const execution = executionQuery.data;
  const pendingIntervention = execution?.interventions.find(
    (item) => item.user_response === null,
  );

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
        {copy.title}
      </h2>

      {moduleTemplates.length === 0 ? (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400">{copy.noTemplates}</p>
      ) : (
        <div className="mt-3 space-y-3">
          <div className="space-y-2 text-start">
            <label htmlFor="workflow-template" className="block text-xs font-medium text-zinc-600">
              {copy.template}
            </label>
            <select
              id="workflow-template"
              value={selectedTemplateId}
              onChange={(event) => setSelectedTemplateId(event.target.value)}
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {moduleTemplates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            disabled={!selectedTemplateId || startMutation.isPending}
            onClick={() =>
              startMutation.mutate({ template_id: selectedTemplateId } satisfies StartWorkflowRequest)
            }
            className="inline-flex h-9 items-center justify-center rounded-lg bg-zinc-900 px-3 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {startMutation.isPending ? copy.starting : copy.start}
          </button>
        </div>
      )}

      {execution ? (
        <div className="mt-4 space-y-3 border-t border-zinc-200 pt-4 dark:border-zinc-800">
          <p className="text-start text-sm text-zinc-700 dark:text-zinc-300">
            {copy.status}: <span className="font-medium">{execution.status}</span> (
            {execution.current_thread_index + 1}/{execution.total_threads})
          </p>

          <ul className="space-y-1 text-start text-xs text-zinc-600 dark:text-zinc-400">
            {execution.thread_executions.map((step) => (
              <li key={step.id}>
                {step.sequence_index + 1}. {step.thread_type} — {step.status}
              </li>
            ))}
          </ul>

          {pendingIntervention ? (
            <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950">
              <p className="text-start text-sm font-medium text-amber-900 dark:text-amber-100">
                {copy.pendingIntervention}
              </p>
              <p className="text-start text-sm text-amber-800 dark:text-amber-200">
                {pendingIntervention.question}
              </p>
              <textarea
                value={interventionResponse}
                onChange={(event) => setInterventionResponse(event.target.value)}
                rows={3}
                className="block w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm dark:border-amber-800 dark:bg-zinc-900"
              />
              <button
                type="button"
                disabled={!interventionResponse.trim() || respondMutation.isPending}
                onClick={() =>
                  respondMutation.mutate({
                    executionId: execution.id,
                    interventionId: pendingIntervention.id,
                    response: interventionResponse.trim(),
                  })
                }
                className="inline-flex h-9 items-center justify-center rounded-lg bg-amber-700 px-3 text-sm font-medium text-white disabled:opacity-60"
              >
                {respondMutation.isPending ? copy.responding : copy.respond}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
