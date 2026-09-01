"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ErrorView } from "@/components/ErrorView";
import { NewRecordingForm } from "@/components/NewRecordingForm";
import { ProcessingView } from "@/components/ProcessingView";
import { ResultView } from "@/components/ResultView";
import { Sidebar } from "@/components/Sidebar";
import { api, ApiError } from "@/lib/api";
import { PROCESSING_STATUSES, TERMINAL_STATUSES } from "@/lib/format";
import { useRecordingPoll } from "@/lib/useRecordingPoll";
import { useRecordingsList } from "@/lib/useRecordingsList";
import type {
  CreateRecordingResponse,
  RecordingDetail,
  RecordingError,
  RecordingStatus,
  Transcript,
  Analysis,
} from "@/lib/types";

/**
 * View modes the center pane can be in.
 *
 * - empty:   URL input form
 * - detail:  a previously-saved recording loaded by id
 * - live:    a freshly-submitted recording being polled
 */
type View =
  | { mode: "empty" }
  | { mode: "detail"; id: string }
  | { mode: "live"; id: string };

const SAFE_FALLBACK_ERROR: RecordingError = {
  code: "PROCESSING_FAILED",
  message: "The recording could not be processed.",
};

function errFromUnknown(e: unknown): ApiError {
  if (e instanceof ApiError) return e;
  return new ApiError(0, "NETWORK_ERROR", "Could not reach the backend.");
}

export default function Page() {
  const list = useRecordingsList();
  const [view, setView] = useState<View>({ mode: "empty" });
  const [detail, setDetail] = useState<RecordingDetail | null>(null);
  const [detailError, setDetailError] = useState<ApiError | null>(null);

  // Live polling only active for `live` mode.
  const liveId = view.mode === "live" ? view.id : null;
  const poll = useRecordingPoll(liveId);

  // Refresh the sidebar exactly once when the polled recording first reaches
  // a terminal state. We intentionally key the effect on a *transition*
  // (previous → current status) so it doesn't fire on every poll tick —
  // `poll` is a fresh object reference every render.
  const liveStatus: RecordingStatus | null =
    poll.phase === "polling" || poll.phase === "timed-out"
      ? poll.detail.status
      : null;
  const prevLiveStatusRef = useRef<RecordingStatus | null>(null);
  useEffect(() => {
    const prev = prevLiveStatusRef.current;
    prevLiveStatusRef.current = liveStatus;
    const becameTerminal =
      liveStatus != null &&
      TERMINAL_STATUSES.includes(liveStatus) &&
      prev !== liveStatus;
    if (becameTerminal) {
      void list.refresh();
    }
  }, [liveStatus, list.refresh]);

  const handleSelectSidebar = useCallback(async (id: string) => {
    setView({ mode: "detail", id });
    setDetail(null);
    setDetailError(null);
    try {
      const d = await api.getRecording(id);
      setDetail(d);
    } catch (e) {
      setDetailError(errFromUnknown(e));
    }
  }, []);

  const handleSubmit = useCallback(
    async (audioUrl: string): Promise<void> => {
      const created: CreateRecordingResponse = await api.createRecording(audioUrl);
      await list.refresh();
      setView({ mode: "live", id: created.id });
    },
    [list]
  );

  const handleNew = useCallback(() => {
    setView({ mode: "empty" });
    setDetail(null);
    setDetailError(null);
  }, []);

  const center = useMemo(
    () => renderCenter({ view, poll, detail, detailError, handleSubmit, handleNew }),
    [view, poll, detail, detailError, handleSubmit, handleNew]
  );

  const selectedId =
    view.mode === "detail" || view.mode === "live" ? view.id : null;

  return (
    <main className="flex h-full">
      <Sidebar
        items={list.items}
        selectedId={selectedId}
        onSelect={handleSelectSidebar}
        onNew={handleNew}
      />
      <section className="flex-1 h-full overflow-y-auto p-8">
        {list.error && view.mode === "empty" ? (
          <div className="mb-4 border border-danger/30 bg-danger/10 rounded-md px-3 py-2 text-sm text-danger">
            Could not load history: {list.error.message}
          </div>
        ) : null}
        {center}
      </section>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Center pane — extracted so the page component stays declarative.
// ---------------------------------------------------------------------------

type RenderCenterArgs = {
  view: View;
  poll: ReturnType<typeof useRecordingPoll>;
  detail: RecordingDetail | null;
  detailError: ApiError | null;
  handleSubmit: (audioUrl: string) => Promise<void>;
  handleNew: () => void;
};

function renderCenter({
  view,
  poll,
  detail,
  detailError,
  handleSubmit,
  handleNew,
}: RenderCenterArgs): React.ReactNode {
  if (view.mode === "empty") {
    return <NewRecordingForm onSubmit={handleSubmit} />;
  }
  if (view.mode === "live") {
    return renderLiveView({ poll, handleNew });
  }
  return renderDetailView({ detail, detailError, handleNew });
}

function renderLiveView({
  poll,
  handleNew,
}: {
  poll: ReturnType<typeof useRecordingPoll>;
  handleNew: () => void;
}): React.ReactNode {
  if (poll.phase === "idle") {
    return (
      <div className="max-w-2xl mx-auto w-full text-fg-muted">Starting...</div>
    );
  }

  if (poll.phase === "error") {
    return (
      <ErrorView
        error={{ code: poll.error.code, message: poll.error.message }}
        onRetry={handleNew}
      />
    );
  }

  const polled = poll.detail;

  if (poll.phase === "timed-out") {
    return <StillProcessing onNew={handleNew} />;
  }

  // poll.phase === "polling"
  if (polled.status === "completed") {
    return renderResultOrFallback(polled);
  }
  if (polled.status === "failed") {
    return (
      <ErrorView error={polled.error ?? SAFE_FALLBACK_ERROR} onRetry={handleNew} />
    );
  }
  return <ProcessingView status={polled.status as ProcessingStatus} />;
}

function renderDetailView({
  detail,
  detailError,
  handleNew,
}: {
  detail: RecordingDetail | null;
  detailError: ApiError | null;
  handleNew: () => void;
}): React.ReactNode {
  if (detailError) {
    return (
      <ErrorView
        error={{ code: detailError.code, message: detailError.message }}
        onRetry={handleNew}
      />
    );
  }
  if (!detail) {
    return (
      <div className="max-w-2xl mx-auto w-full text-fg-muted">Loading...</div>
    );
  }
  if (detail.status === "completed") {
    return renderResultOrFallback(detail);
  }
  if (PROCESSING_STATUSES.includes(detail.status)) {
    return <StillProcessing onNew={handleNew} />;
  }
  if (detail.status === "failed") {
    return (
      <ErrorView error={detail.error ?? SAFE_FALLBACK_ERROR} onRetry={handleNew} />
    );
  }
  return (
    <div className="max-w-2xl mx-auto w-full text-fg-muted">Unknown state.</div>
  );
}

function renderResultOrFallback(detail: RecordingDetail): React.ReactNode {
  const transcript: Transcript | undefined = detail.transcript ?? undefined;
  const analysis: Analysis | undefined = detail.analysis ?? undefined;
  if (!transcript || !analysis) {
    return (
      <div className="max-w-2xl mx-auto w-full text-fg-muted">
        Recording completed but no result was returned.
      </div>
    );
  }
  return (
    <ResultView
      analysis={analysis}
      transcript={transcript}
      createdAt={detail.createdAt}
      completedAt={detail.completedAt}
    />
  );
}

function StillProcessing({ onNew }: { onNew: () => void }) {
  return (
    <div className="max-w-2xl mx-auto w-full">
      <h1 className="text-xl font-semibold text-fg">Still processing</h1>
      <p className="mt-2 text-sm text-fg-muted">
        This recording is taking longer than expected. You can close this page
        or start a new analysis — the recording will be saved when it finishes,
        and you can find it in the sidebar.
      </p>
      <button
        type="button"
        onClick={onNew}
        className="mt-6 px-4 py-2 rounded-md bg-accent text-bg font-medium hover:bg-accent-hover transition"
      >
        Start a new analysis
      </button>
    </div>
  );
}

// Local alias to avoid re-importing the same type from `@/lib/types` with
// different narrowing — used only inside renderLiveView.
type ProcessingStatus = Extract<
  RecordingStatus,
  "pending" | "downloading" | "transcribing" | "analyzing" | "saving"
>;
