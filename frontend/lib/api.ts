/**
 * Typed REST client for the Voxera backend (Phase 4 version — eager module-load
 * check). Lazy version that defers the throw to first request lands in the
 * frontend-loop fix commit.
 */

import type {
  ApiErrorBody,
  CreateRecordingResponse,
  RecordingDetail,
  RecordingListResponse,
} from "./types";

const BASE_URL = (() => {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set. Copy frontend/.env.example to .env.local."
    );
  }
  return raw.replace(/\/$/, "");
})();

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
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
      // ignore JSON parse error
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
