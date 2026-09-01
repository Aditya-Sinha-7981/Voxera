"use client";

/**
 * Polls a recording's status with a 2s interval and a 5-minute cap (ARCHITECTURE §5).
 * Stops on `completed` or `failed`. Returns the latest `RecordingDetail`.
 *
 * The hook does not retry on transient errors — the parent decides what to do
 * with the error object.
 */

import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { RecordingDetail } from "@/lib/types";

const POLL_INTERVAL_MS = 2_000;
const MAX_POLL_DURATION_MS = 5 * 60 * 1_000; // 5 minutes

type PollState =
  | { phase: "idle" }
  | { phase: "polling"; detail: RecordingDetail }
  | { phase: "timed-out"; detail: RecordingDetail }
  | { phase: "error"; error: ApiError };

export function useRecordingPoll(recordingId: string | null): PollState {
  const [state, setState] = useState<PollState>({ phase: "idle" });
  const startedAt = useRef<number>(0);
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (!recordingId) {
      setState({ phase: "idle" });
      return;
    }

    stoppedRef.current = false;
    startedAt.current = Date.now();

    let timer: ReturnType<typeof setTimeout> | null = null;

    const tick = async () => {
      if (stoppedRef.current) return;
      try {
        const detail = await api.getRecording(recordingId);
        if (stoppedRef.current) return;

        if (detail.status === "completed" || detail.status === "failed") {
          setState({ phase: "polling", detail });
          stoppedRef.current = true;
          return;
        }

        const elapsed = Date.now() - startedAt.current;
        if (elapsed >= MAX_POLL_DURATION_MS) {
          setState({ phase: "timed-out", detail });
          stoppedRef.current = true;
          return;
        }

        setState({ phase: "polling", detail });
        timer = setTimeout(tick, POLL_INTERVAL_MS);
      } catch (err) {
        if (stoppedRef.current) return;
        stoppedRef.current = true;
        const apiErr =
          err instanceof ApiError
            ? err
            : new ApiError(0, "NETWORK_ERROR", "Could not reach the backend.");
        setState({ phase: "error", error: apiErr });
      }
    };

    void tick();

    return () => {
      stoppedRef.current = true;
      if (timer) clearTimeout(timer);
    };
  }, [recordingId]);

  return state;
}
