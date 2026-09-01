"use client";

import { ActionItemsList } from "./ActionItemsList";
import { TranscriptView } from "./TranscriptView";
import { formatTimestamp, sentimentClasses } from "@/lib/format";
import type { Analysis, Transcript } from "@/lib/types";

type Props = {
  analysis: Analysis;
  transcript: Transcript;
  createdAt?: string | null;
  completedAt?: string | null;
};

export function ResultView({
  analysis,
  transcript,
  createdAt,
  completedAt,
}: Props) {
  return (
    <div className="max-w-3xl mx-auto w-full space-y-8">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-fg-subtle">
          {createdAt ? (
            <span>{formatTimestamp(createdAt)}</span>
          ) : null}
          {completedAt ? (
            <>
              <span>·</span>
              <span>completed {formatTimestamp(completedAt)}</span>
            </>
          ) : null}
        </div>
        <h1 className="text-2xl font-semibold text-fg">{analysis.title}</h1>
        <div className="flex flex-wrap gap-2">
          <span
            className={`text-[11px] uppercase tracking-wide px-2 py-0.5 rounded border ${sentimentClasses(
              analysis.sentiment.label
            )}`}
          >
            {analysis.sentiment.label} · {analysis.sentiment.score.toFixed(2)}
          </span>
          <span className="text-[11px] uppercase tracking-wide px-2 py-0.5 rounded border border-border-soft text-fg-muted">
            {analysis.conversationType.replace(/_/g, " ")}
          </span>
          {analysis.followUpRequired ? (
            <span className="text-[11px] uppercase tracking-wide px-2 py-0.5 rounded border border-warn/30 bg-warn/15 text-warn">
              follow-up
            </span>
          ) : null}
        </div>
      </header>

      <Section label="Summary" testId="analysis-summary">
        <p className="text-sm text-fg-muted leading-relaxed">
          {analysis.summary}
        </p>
      </Section>

      <Section label="Key points">
        {analysis.keyPoints.length === 0 ? (
          <p className="text-sm text-fg-subtle italic">None.</p>
        ) : (
          <ul className="list-disc list-inside space-y-1 text-sm text-fg-muted">
            {analysis.keyPoints.map((kp, i) => (
              <li key={i}>{kp}</li>
            ))}
          </ul>
        )}
      </Section>

      {analysis.complaints.length > 0 ? (
        <Section label="Complaints">
          <ul className="list-disc list-inside space-y-1 text-sm text-fg-muted">
            {analysis.complaints.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {analysis.requests.length > 0 ? (
        <Section label="Requests">
          <ul className="list-disc list-inside space-y-1 text-sm text-fg-muted">
            {analysis.requests.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      <Section label="Action items">
        <ActionItemsList items={analysis.actionItems} />
      </Section>

      {analysis.importantDetails.length > 0 ? (
        <Section label="Important details">
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
            {analysis.importantDetails.map((d, i) => (
              <div key={i} className="contents">
                <dt className="text-fg-subtle">{d.key}</dt>
                <dd className="text-fg-muted">{d.value}</dd>
              </div>
            ))}
          </dl>
        </Section>
      ) : null}

      <Section label="Transcript">
        <TranscriptView transcript={transcript} />
      </Section>
    </div>
  );
}

function Section({
  label,
  testId,
  children,
}: {
  label: string;
  testId?: string;
  children: React.ReactNode;
}) {
  return (
    <section data-testid={testId} className="space-y-2">
      <h2 className="text-xs uppercase tracking-wider text-fg-subtle">
        {label}
      </h2>
      {children}
    </section>
  );
}
