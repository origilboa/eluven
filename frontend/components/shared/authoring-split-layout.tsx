"use client";

import type { ReactNode } from "react";

type AuthoringSplitLayoutProps = {
  form: ReactNode;
  assistant?: ReactNode;
};

export function AuthoringSplitLayout({ form, assistant }: AuthoringSplitLayoutProps) {
  if (!assistant) {
    return <div className="space-y-4">{form}</div>;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2 lg:items-start">
      <div className="space-y-4">{form}</div>
      {assistant}
    </div>
  );
}
