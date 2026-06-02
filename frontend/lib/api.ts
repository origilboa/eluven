import { getSession } from "next-auth/react";

import type { ApiErrorBody } from "@/lib/types/api";

const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  status: number;

  body: ApiErrorBody | null;

  constructor(message: string, status: number, body: ApiErrorBody | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function serverApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

/** Resolve a path to the backend API (browser uses Next.js rewrite proxy). */
export function resolveApiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const apiPath = normalized.startsWith(API_PREFIX)
    ? normalized
    : `${API_PREFIX}${normalized}`;

  if (typeof window === "undefined") {
    return `${serverApiBase()}${apiPath}`;
  }

  return `/api/backend${apiPath}`;
}

async function buildHeaders(
  initHeaders?: HeadersInit,
  accessToken?: string,
): Promise<Headers> {
  const headers = new Headers(initHeaders);

  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

async function resolveAccessToken(explicitToken?: string): Promise<string | undefined> {
  if (explicitToken) {
    return explicitToken;
  }

  if (typeof window === "undefined") {
    return undefined;
  }

  const session = await getSession();
  return session?.accessToken;
}

async function request<T>(
  method: string,
  path: string,
  options: {
    body?: unknown;
    headers?: HeadersInit;
    accessToken?: string;
    skipJsonContentType?: boolean;
  } = {},
): Promise<T> {
  const { body, headers: initHeaders, accessToken, skipJsonContentType } = options;
  const token = await resolveAccessToken(accessToken);
  const headers = await buildHeaders(initHeaders, token);

  if (skipJsonContentType) {
    headers.delete("Content-Type");
  }

  const response = await fetch(resolveApiUrl(path), {
    method,
    headers,
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
    credentials: "include",
  });

  if (!response.ok) {
    let errorBody: ApiErrorBody | null = null;
    try {
      errorBody = (await response.json()) as ApiErrorBody;
    } catch {
      errorBody = null;
    }

    const detail = errorBody?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : `Request failed with status ${response.status}`;

    throw new ApiError(message, response.status, errorBody);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  get<T>(path: string, options?: { headers?: HeadersInit; accessToken?: string }) {
    return request<T>("GET", path, options);
  },

  post<T>(
    path: string,
    body?: unknown,
    options?: { headers?: HeadersInit; accessToken?: string },
  ) {
    return request<T>("POST", path, { ...options, body });
  },

  patch<T>(
    path: string,
    body?: unknown,
    options?: { headers?: HeadersInit; accessToken?: string },
  ) {
    return request<T>("PATCH", path, { ...options, body });
  },

  put<T>(
    path: string,
    body?: unknown,
    options?: { headers?: HeadersInit; accessToken?: string },
  ) {
    return request<T>("PUT", path, { ...options, body });
  },

  delete<T>(path: string, options?: { headers?: HeadersInit; accessToken?: string }) {
    return request<T>("DELETE", path, options);
  },

  upload<T>(
    path: string,
    file: File,
    options?: { headers?: HeadersInit; accessToken?: string },
  ) {
    const formData = new FormData();
    formData.append("file", file);
    return request<T>("POST", path, {
      ...options,
      body: formData,
      skipJsonContentType: true,
    });
  },

  async download(
    path: string,
    options?: { headers?: HeadersInit; accessToken?: string },
  ): Promise<{ blob: Blob; filename: string | null }> {
    const token = await resolveAccessToken(options?.accessToken);
    const headers = await buildHeaders(options?.headers, token);
    headers.delete("Content-Type");

    const response = await fetch(resolveApiUrl(path), {
      method: "GET",
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      throw new ApiError(`Download failed with status ${response.status}`, response.status);
    }

    const disposition = response.headers.get("Content-Disposition");
    const filenameMatch = disposition?.match(/filename="([^"]+)"/);
    const blob = await response.blob();
    return { blob, filename: filenameMatch?.[1] ?? null };
  },
};
