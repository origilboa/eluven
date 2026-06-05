"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  InstructionSetEditor,
  type ThreadTypeOption,
} from "@/components/instructions/instruction-set-editor";
import { api } from "@/lib/api";
import type { ActivityLibraryEntryResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ClusterInstructionPanelProps = {
  locale: Locale;
  clusterId: string;
  moduleType: string;
};

export function ClusterInstructionPanel({
  locale,
  clusterId,
  moduleType,
}: ClusterInstructionPanelProps) {
  const [selectedThreadType, setSelectedThreadType] = useState<string | null>(null);

  const { data: activityEntries } = useQuery({
    queryKey: ["activity-library", moduleType],
    queryFn: () =>
      api.get<ActivityLibraryEntryResponse[]>(
        `/activity-library?module_type=${encodeURIComponent(moduleType)}`,
      ),
  });

  const threadTypeOptions = useMemo<ThreadTypeOption[]>(() => {
    const allLabel =
      locale === "he" ? "כל סוגי השרשורים" : "All thread types";
    const options: ThreadTypeOption[] = [{ value: null, label: allLabel }];
    for (const entry of activityEntries ?? []) {
      options.push({ value: entry.thread_type, label: entry.display_name });
    }
    return options;
  }, [activityEntries, locale]);

  const copy =
    locale === "he"
      ? {
          title: "הוראות Cluster",
          subtitle:
            "הוראות ברמת המטלה (Assignment) — חלות על כל ההגשות ב-cluster. ניתן להגביל לסוג thread ספציפי.",
        }
      : {
          title: "Cluster instructions",
          subtitle:
            "Assignment-level instructions applied to every submission in this cluster. Optionally scope to one thread type.",
        };

  const basePath = `/instructions/clusters/${clusterId}`;

  return (
    <InstructionSetEditor
      locale={locale}
      queryKey={["instructions", "cluster", clusterId]}
      fetchPath={basePath}
      createPath={basePath}
      activatePath={`${basePath}/activate`}
      title={copy.title}
      subtitle={copy.subtitle}
      threadTypeOptions={threadTypeOptions}
      selectedThreadType={selectedThreadType}
      onThreadTypeChange={setSelectedThreadType}
      assistantScope={{
        authoring_target: "instruction_set",
        level: "cluster",
        cluster_id: clusterId,
        module_type: moduleType,
      }}
    />
  );
}
