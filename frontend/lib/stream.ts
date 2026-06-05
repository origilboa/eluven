import { getSession } from "next-auth/react";

import { resolveApiUrl } from "@/lib/api";
import type {
  ActivityOrchestratorStreamRequest,
  InstructionAssistantStreamRequest,
  InstructionIntegrityRemediateRequest,
  PromptAssistantStreamRequest,
  StreamEvent,
} from "@/lib/types/api";

function parseSseChunk(buffer: string): { events: StreamEvent[]; remainder: string } {
  const events: StreamEvent[] = [];
  const parts = buffer.split("\n\n");
  const remainder = parts.pop() ?? "";

  for (const part of parts) {
    const line = part
      .split("\n")
      .find((entry) => entry.startsWith("data: "));
    if (!line) {
      continue;
    }
    try {
      events.push(JSON.parse(line.slice(6)) as StreamEvent);
    } catch {
      // Ignore malformed SSE payloads.
    }
  }

  return { events, remainder };
}

async function consumeSseResponse(
  response: Response,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  if (!response.ok) {
    throw new Error(`Stream request failed (${response.status})`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Stream body unavailable");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseChunk(buffer);
    buffer = parsed.remainder;
    for (const event of parsed.events) {
      onEvent(event);
    }
  }

  if (buffer.trim()) {
    const parsed = parseSseChunk(`${buffer}\n\n`);
    for (const event of parsed.events) {
      onEvent(event);
    }
  }
}

export async function streamThreadMessage(
  threadId: string,
  content: string,
  onEvent: (event: StreamEvent) => void,
  promptId?: string | null,
): Promise<void> {
  const session = await getSession();
  if (!session?.accessToken) {
    throw new Error("Not authenticated");
  }

  const body: { content: string; prompt_id?: string } = { content };
  if (promptId) {
    body.prompt_id = promptId;
  }

  const response = await fetch(resolveApiUrl(`/threads/${threadId}/stream`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify(body),
  });

  await consumeSseResponse(response, onEvent);
}

export async function streamInstructionAssistant(
  request: InstructionAssistantStreamRequest,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const session = await getSession();
  if (!session?.accessToken) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(resolveApiUrl("/instructions/assistant/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify(request),
  });

  await consumeSseResponse(response, onEvent);
}

export async function streamInstructionIntegrityRemediate(
  request: InstructionIntegrityRemediateRequest,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const session = await getSession();
  if (!session?.accessToken) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(
    resolveApiUrl("/instructions/assistant/integrity-check/remediate"),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.accessToken}`,
      },
      body: JSON.stringify(request),
    },
  );

  await consumeSseResponse(response, onEvent);
}

export async function streamPromptAssistant(
  request: PromptAssistantStreamRequest,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const session = await getSession();
  if (!session?.accessToken) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(resolveApiUrl("/activity-library/prompts/assistant/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify(request),
  });

  await consumeSseResponse(response, onEvent);
}

export async function streamActivityOrchestrator(
  request: ActivityOrchestratorStreamRequest,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const session = await getSession();
  if (!session?.accessToken) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(resolveApiUrl("/activity-library/assistant/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify(request),
  });

  await consumeSseResponse(response, onEvent);
}
