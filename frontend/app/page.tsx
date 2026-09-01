"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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
} from "@/lib/types";

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

  const liveId = view.mode === "live" ? view.id : null;
  const poll = useRecordingPoll(liveId);

  // Note: original Phase 4 implementation keyed the effect on `poll`, which
  // is a fresh object reference every render — this caused an infinite list
  // refresh loop during polling. Fixed in a follow-up commit.
  useEffect(() => {
    if (poll.phase === "polling" && TERMINAL_STATUSES.includes(poll.detail.status)) {
      void list.refresh();
    }
  }, [poll, list]);

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

function renderCenter({
  view,
  poll,
  detail,
  detailError,
  handleSubmit,
  handleNew,
}: {
  view: View;
  poll: ReturnType<typeof useRecordingPoll>;
  detail: RecordingDetail | null;
  detailError: ApiError | null;
  handleSubmit: (audioUrl: string) => Promise<void>;
  handleNew: () => void;
}): React.ReactNode {
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
    return <div className="max-w-2xl mx-auto w-full text-fg-muted">Starting...</div>;
  }
  if (poll.phase === "error") {
    return <ErrorView error={{ code: poll.error.code, message: poll.error.message }} onRetry={handleNew} />;
  }
  const polled = poll.detail;
  if (poll.phase === "timed-out") {
    return <StillProcessing onNew={handleNew} />;
  }
  if (polled.status === "completed") {
    return renderResultOrFallback(polled);
  }
  if (polled.status === "failed") {
    return <ErrorView error={polled.error ?? SAFE_FALLBACK_ERROR} onRetry={handleNew} />;
  }
  return <ProcessingView status={polled.status as "pending" | "downloading" | "transcribing" | "analyzing" | "saving"} />;
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
    return <ErrorView error={{ code: detailError.code, message: detailError.message }} onRetry={handleNew} />;
  }
  if (!detail) {
    return <div className="max-w-2xl mx-auto w-full text-fg-muted">Loading...</div>;
  }
  if (detail.status === "completed") {
    return renderResultOrFallback(detail);
  }
  if (PROCESSING_STATUSES.includes(detail.status)) {
    return <StillProcessing onNew={handleNew} />;
  }
  if (detail.status === "failed") {
    return <ErrorView error={detail.error ?? SAFE_FALLBACK_ERROR} onRetry={handleNew} />;
  }
  return <div className="max-w-2xl mx-auto w-full text-fg-muted">Unknown state.</div>;
}

function renderResultOrFallback(detail: RecordingDetail): React.ReactNode {
  if (!detail.transcript || !detail.analysis) {
    return (
      <div className="max-w-2xl mx-auto w-full text-fg-muted">
        Recording completed but no result was returned.
      </div>
    );
  }
  return (
    <ResultView
      analysis={detail.analysis}
      transcript={detail.transcript}
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
        This recording is taking longer than expected. Try again later.
      </p>
      <button type="button" onClick={onNew} className="mt-6 px-4 py-2 rounded-md bg-accent text-bg font-medium hover:bg-accent-hover transition">
        Start a new analysis
      </button>
    </div>
  );
}
