"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type {
  InstructionAssistantScope,
  InstructionIntegrityCheckResponse,
  InstructionIntegrityIssue,
} from "@/lib/types/api";

export type InstructionDraftGateStatus =
  | "idle"
  | "checking"
  | "passed"
  | "failed"
  | "stale";

function normalizeDraftContent(content: string): string {
  return content.replace(/\r\n/g, "\n").trim();
}

export type InstructionDraftGateState = {
  status: InstructionDraftGateStatus;
  approvalToken: string | null;
  approvedContent: string | null;
  issues: InstructionIntegrityIssue[];
  summary: string | null;
  expiresAt: string | null;
  checkError: string | null;
  canSave: boolean;
  runIntegrityCheck: (draftContent: string) => Promise<InstructionIntegrityCheckResponse | null>;
  resetGate: () => void;
};

export function useInstructionDraftGate(
  scope: InstructionAssistantScope,
  draftContent: string,
  locale: "en" | "he",
): InstructionDraftGateState {
  const [status, setStatus] = useState<InstructionDraftGateStatus>("idle");
  const [approvalToken, setApprovalToken] = useState<string | null>(null);
  const [approvedContent, setApprovedContent] = useState<string | null>(null);
  const [issues, setIssues] = useState<InstructionIntegrityIssue[]>([]);
  const [summary, setSummary] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  const resetGate = useCallback(() => {
    setStatus("idle");
    setApprovalToken(null);
    setApprovedContent(null);
    setIssues([]);
    setSummary(null);
    setExpiresAt(null);
    setCheckError(null);
  }, []);

  useEffect(() => {
    if (!approvedContent || !approvalToken) {
      return;
    }
    if (normalizeDraftContent(draftContent) !== approvedContent) {
      setStatus("stale");
      setApprovalToken(null);
    }
  }, [approvalToken, approvedContent, draftContent]);

  const runIntegrityCheck = useCallback(
    async (content: string): Promise<InstructionIntegrityCheckResponse | null> => {
      const trimmed = content.trim();
      if (!trimmed) {
        setCheckError("Add draft text before running an integrity check.");
        return null;
      }

      setStatus("checking");
      setCheckError(null);
      setIssues([]);
      setSummary(null);

      try {
        const response = await api.post<InstructionIntegrityCheckResponse>(
          "/instructions/assistant/integrity-check",
          {
            scope,
            draft_content: trimmed,
            locale,
          },
        );

        setSummary(response.summary);
        setIssues(response.issues);

        if (response.status === "pass" && response.approval_token) {
          setStatus("passed");
          setApprovalToken(response.approval_token);
          setApprovedContent(normalizeDraftContent(trimmed));
          setExpiresAt(response.expires_at);
          return response;
        }

        setStatus("failed");
        setApprovalToken(null);
        setApprovedContent(null);
        setExpiresAt(null);
        return response;
      } catch (error) {
        setStatus("failed");
        setApprovalToken(null);
        setApprovedContent(null);
        setCheckError(error instanceof Error ? error.message : "Integrity check failed");
        return null;
      }
    },
    [locale, scope],
  );

  const normalizedDraft = normalizeDraftContent(draftContent);
  const canSave =
    status === "passed" &&
    Boolean(approvalToken) &&
    Boolean(approvedContent) &&
    normalizedDraft === approvedContent &&
    Boolean(normalizedDraft);

  return {
    status,
    approvalToken,
    approvedContent,
    issues,
    summary,
    expiresAt,
    checkError,
    canSave,
    runIntegrityCheck,
    resetGate,
  };
}
