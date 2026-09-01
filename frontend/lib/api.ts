/**
 * Typed REST client for the Voxera backend.
 *
 * Backend URL is read from `NEXT_PUBLIC_API_URL`. The variable is resolved
 * lazily on the first API call so the page can still render during
 * `next build` even when the env var is not yet set in CI.
 */

import type {
  ApiErrorBody,
  CreateRecordingResponse,
  RecordingDetail,
  RecordingListResponse,
} from "./types";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function getBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) {
    throw new ApiError(
      0,
      "CONFIGURATION_ERROR",
      "NEXT_PUBLIC_API_URL is not set. Copy frontend/.env.example to .env.local."
    );
  }
  return raw.replace(/\/$/, "");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // ignore JSON parse error, fall back to defaults below.
    }
    const code = body?.error?.code ?? "HTTP_ERROR";
    const message = body?.error?.message ?? `Request failed: ${response.status}`;
    throw new ApiError(response.status, code, message);
  }

  return (await response.json()) as T;
}

export const api = {
  createRecording(audioUrl: string): Promise<CreateRecordingResponse> {
    return request<CreateRecordingResponse>("/api/v1/recordings", {
      method: "POST",
      body: JSON.stringify({ audioUrl }),
    });
  },
  listRecordings(params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<RecordingListResponse> {
    const search = new URLSearchParams();
    if (params?.limit != null) search.set("limit", String(params.limit));
    if (params?.offset != null) search.set("offset", String(params.offset));
    if (params?.status) search.set("status", params.status);
    const qs = search.toString();
    return request<RecordingListResponse>(
      `/api/v1/recordings${qs ? `?${qs}` : ""}`
    );
  },
  getRecording(id: string): Promise<RecordingDetail> {
    return request<RecordingDetail>(`/api/v1/recordings/${encodeURIComponent(id)}`);
  },
};
