"use client";

function parseFreeformTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export { parseFreeformTags };
