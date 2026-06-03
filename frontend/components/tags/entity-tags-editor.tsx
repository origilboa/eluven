"use client";

type EntityTagsEditorProps = {
  locale: "en" | "he";
  structuredTags: Record<string, string>;
  freeformTags: string;
  onStructuredTagsChange: (tags: Record<string, string>) => void;
  onFreeformTagsChange: (value: string) => void;
  structuredFields?: Array<{ key: string; label: string; required?: boolean }>;
};

export function EntityTagsEditor({
  locale,
  structuredTags,
  freeformTags,
  onStructuredTagsChange,
  onFreeformTagsChange,
  structuredFields = [],
}: EntityTagsEditorProps) {
  const copy =
    locale === "he"
      ? {
          freeform: "תגיות חופשיות (מופרדות בפסיק)",
          freeformPlaceholder: "honors-section, resit",
        }
      : {
          freeform: "Freeform tags (comma-separated)",
          freeformPlaceholder: "honors-section, resit",
        };

  return (
    <div className="space-y-4">
      {structuredFields.map((field) => (
        <div key={field.key} className="space-y-2 text-start">
          <label htmlFor={`tag-${field.key}`} className="block text-sm font-medium">
            {field.label}
            {field.required ? " *" : ""}
          </label>
          <input
            id={`tag-${field.key}`}
            required={field.required}
            value={structuredTags[field.key] ?? ""}
            onChange={(event) =>
              onStructuredTagsChange({
                ...structuredTags,
                [field.key]: event.target.value,
              })
            }
            className="block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
      ))}

      <div className="space-y-2 text-start">
        <label htmlFor="freeform-tags" className="block text-sm font-medium">
          {copy.freeform}
        </label>
        <input
          id="freeform-tags"
          value={freeformTags}
          onChange={(event) => onFreeformTagsChange(event.target.value)}
          placeholder={copy.freeformPlaceholder}
          className="block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>
    </div>
  );
}
