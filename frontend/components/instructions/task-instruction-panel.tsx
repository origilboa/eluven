"use client";

import { InstructionSetEditor } from "@/components/instructions/instruction-set-editor";
import type { Locale } from "@/i18n.config";

type TaskInstructionPanelProps = {
  locale: Locale;
  taskId: string;
  moduleType: string;
};

export function TaskInstructionPanel({
  locale,
  taskId,
  moduleType,
}: TaskInstructionPanelProps) {
  const copy =
    locale === "he"
      ? {
          title: "הוראות Task",
          subtitle: "הוראות ברמת המשימה — חלות על כל השרשורים במשימה זו.",
        }
      : {
          title: "Task instructions",
          subtitle: "Task-wide instructions applied to every thread on this task.",
        };

  const basePath = `/instructions/tasks/${taskId}`;

  return (
    <InstructionSetEditor
      locale={locale}
      queryKey={["instructions", "task", taskId]}
      fetchPath={basePath}
      createPath={basePath}
      activatePath={`${basePath}/activate`}
      title={copy.title}
      subtitle={copy.subtitle}
      assistantScope={{
        authoring_target: "instruction_set",
        level: "task",
        task_id: taskId,
        module_type: moduleType,
      }}
    />
  );
}
