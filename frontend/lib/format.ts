/**
 * Pure formatting helpers — no React, no fetch.
 *
 * Kept here so component code stays declarative and so unit tests can target
 * these in isolation (Phase 5).
 */

import type { RecordingStatus } from "./types";

export const PROCESSING_STATUSES: RecordingStatus[] = [
  "pending",
  "downloading",
  "transcribing",
  "analyzing",
  "saving",
];

export const TERMINAL_STATUSES: RecordingStatus[] = ["completed", "failed"];

export function isProcessing(status: RecordingStatus): boolean {
  return PROCESSING_STATUSES.includes(status);
}

/**
 * Map a backend-reported status to a user-friendly progress message (§5).
 */
export function statusToMessage(status: RecordingStatus): string {
  switch (status) {
    case "pending":
      return "Waiting to start...";
    case "downloading":
      return "Downloading audio...";
    case "transcribing":
      return "Transcribing conversation...";
    case "analyzing":
      return "Analyzing conversation...";
    case "saving":
      return "Saving results...";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
  }
}

export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatSidebarTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const sameYesterday =
    d.getFullYear() === yesterday.getFullYear() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getDate() === yesterday.getDate();

  if (sameDay) {
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  if (sameYesterday) return "Yesterday";
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function sentimentClasses(label: string | null | undefined): string {
  switch (label) {
    case "positive":
      return "bg-ok/15 text-ok border-ok/30";
    case "negative":
      return "bg-danger/15 text-danger border-danger/30";
    case "neutral":
    default:
      return "bg-fg-subtle/15 text-fg-muted border-fg-subtle/30";
  }
}

export function priorityClasses(p: string): string {
  switch (p) {
    case "high":
      return "bg-danger/15 text-danger border-danger/30";
    case "medium":
      return "bg-warn/15 text-warn border-warn/30";
    case "low":
    default:
      return "bg-fg-subtle/15 text-fg-muted border-fg-subtle/30";
  }
}
