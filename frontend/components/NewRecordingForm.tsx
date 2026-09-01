"use client";

import { useState, FormEvent } from "react";

import { ApiError } from "@/lib/api";

type Props = {
  onSubmit: (audioUrl: string) => Promise<void> | void;
};

export function NewRecordingForm({ onSubmit }: Props) {
  const [audioUrl, setAudioUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const trimmed = audioUrl.trim();
    if (!trimmed) {
      setError("Please paste an audio URL.");
      return;
    }
    try {
      setSubmitting(true);
      await onSubmit(trimmed);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not start processing.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto w-full">
      <h1 className="text-2xl font-semibold text-fg">
        Analyze a hotel conversation
      </h1>
      <p className="mt-2 text-fg-muted">
        Paste an audio recording URL below. The recording will be downloaded
        temporarily, transcribed, and analyzed.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        <div>
          <label
            htmlFor="audio-url"
            className="block text-sm font-medium text-fg-muted mb-1.5"
          >
            Audio URL
          </label>
          <input
            id="audio-url"
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            placeholder="https://example.com/recording.mp3"
            value={audioUrl}
            onChange={(e) => setAudioUrl(e.target.value)}
            disabled={submitting}
            className="w-full px-3 py-2.5 bg-bg-soft border border-border rounded-md text-fg placeholder:text-fg-subtle focus:outline-none focus:border-accent disabled:opacity-60"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || !audioUrl.trim()}
          className="px-4 py-2.5 rounded-md bg-accent text-bg font-medium hover:bg-accent-hover transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? "Submitting..." : "Analyze Recording"}
        </button>

        {error ? (
          <div
            role="alert"
            className="text-sm text-danger border border-danger/30 bg-danger/10 rounded-md px-3 py-2"
          >
            {error}
          </div>
        ) : null}
      </form>
    </div>
  );
}
