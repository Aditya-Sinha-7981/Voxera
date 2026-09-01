"use client";

import type { Transcript } from "@/lib/types";

function formatTime(seconds: number | null): string {
  if (seconds == null) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function TranscriptView({ transcript }: { transcript: Transcript }) {
  if (!transcript.text && transcript.segments.length === 0) {
    return (
      <p className="text-sm text-fg-subtle italic">No transcript available.</p>
    );
  }

  if (transcript.segments.length === 0) {
    // Fallback: show the full transcript text.
    return (
      <div className="whitespace-pre-wrap text-sm text-fg-muted leading-relaxed">
        {transcript.text}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {transcript.segments.map((seg, idx) => {
        const speakerLabel = seg.speaker ?? "Speaker";
        const roleLabel = seg.role === "hotel_staff" ? "Staff" : seg.role === "guest" ? "Guest" : null;
        return (
          <div key={idx} className="text-sm leading-relaxed">
            <div className="flex items-baseline gap-2 text-[11px] text-fg-subtle uppercase tracking-wide">
              <span>{speakerLabel}</span>
              {roleLabel ? <span>· {roleLabel}</span> : null}
              {seg.start != null ? (
                <span className="font-mono">{formatTime(seg.start)}</span>
              ) : null}
            </div>
            <div className="mt-0.5 text-fg whitespace-pre-wrap">{seg.text}</div>
          </div>
        );
      })}
    </div>
  );
}
