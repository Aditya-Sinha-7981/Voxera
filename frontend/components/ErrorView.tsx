"use client";

import type { RecordingError } from "@/lib/types";

type Props = {
  error: RecordingError;
  onRetry?: () => void;
};

export function ErrorView({ error, onRetry }: Props) {
  return (
    <div className="max-w-2xl mx-auto w-full">
      <div className="text-sm uppercase tracking-wide text-danger">
        Processing failed
      </div>
      <h1 className="mt-2 text-xl font-semibold text-fg">
        This recording couldn&apos;t be processed
      </h1>
      <div className="mt-6 border border-danger/30 bg-danger/10 rounded-md p-4">
        <div className="text-xs uppercase tracking-wide text-danger">
          {error.code}
        </div>
        <div className="mt-1 text-sm text-fg">{error.message}</div>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-6 px-4 py-2 rounded-md bg-accent text-bg font-medium hover:bg-accent-hover transition"
        >
          Start a new analysis
        </button>
      ) : null}
    </div>
  );
}
