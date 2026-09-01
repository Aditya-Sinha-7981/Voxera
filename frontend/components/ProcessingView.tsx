"use client";

import { statusToMessage } from "@/lib/format";
import type { RecordingStatus } from "@/lib/types";

type Props = {
  status: RecordingStatus;
};

export function ProcessingView({ status }: Props) {
  return (
    <div className="max-w-2xl mx-auto w-full">
      <div className="text-sm uppercase tracking-wide text-fg-subtle">
        Processing
      </div>
      <h1 className="mt-2 text-2xl font-semibold text-fg">
        {statusToMessage(status)}
      </h1>

      <div className="mt-8 space-y-2.5">
        {(
          [
            "pending",
            "downloading",
            "transcribing",
            "analyzing",
            "saving",
          ] as RecordingStatus[]
        ).map((step, i) => {
          const reached =
            indexOf(status, [
              "pending",
              "downloading",
              "transcribing",
              "analyzing",
              "saving",
            ]) >= i;
          return (
            <div
              key={step}
              className="flex items-center gap-3 text-sm"
              aria-current={step === status ? "step" : undefined}
            >
              <div
                className={`h-2 w-2 rounded-full ${
                  step === status
                    ? "bg-accent animate-pulse"
                    : reached
                      ? "bg-ok"
                      : "bg-fg-subtle/40"
                }`}
              />
              <span
                className={
                  step === status
                    ? "text-fg"
                    : reached
                      ? "text-fg-muted"
                      : "text-fg-subtle"
                }
              >
                {statusToMessage(step)}
              </span>
            </div>
          );
        })}
      </div>

      <p className="mt-8 text-sm text-fg-subtle">
        You can refresh this page or come back — the recording will be saved
        once it finishes.
      </p>
    </div>
  );
}

function indexOf<T>(value: T, list: T[]): number {
  return list.indexOf(value);
}
