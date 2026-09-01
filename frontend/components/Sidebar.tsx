"use client";

import { RecordingListItem } from "@/lib/types";
import { formatSidebarTime, sentimentClasses } from "@/lib/format";

type Props = {
  items: RecordingListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
};

export function Sidebar({ items, selectedId, onSelect, onNew }: Props) {
  return (
    <aside className="w-72 shrink-0 h-full bg-bg-soft border-r border-border flex flex-col">
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="text-fg font-semibold tracking-tight">Voxera</div>
        <button
          type="button"
          onClick={onNew}
          className="text-xs px-2 py-1 rounded bg-accent/15 text-accent border border-accent/30 hover:bg-accent/25 transition"
        >
          + New
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {items.length === 0 ? (
          <div className="text-fg-subtle text-sm px-2 py-3">
            No recordings yet.
          </div>
        ) : (
          items.map((item) => {
            const selected = item.id === selectedId;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect(item.id)}
                className={`w-full text-left rounded-md px-3 py-2 transition border ${
                  selected
                    ? "bg-bg-panel border-border-soft"
                    : "border-transparent hover:bg-bg-panel/60"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm text-fg font-medium truncate">
                    {item.title || "Untitled conversation"}
                  </div>
                  {item.status === "failed" ? (
                    <span className="shrink-0 text-[10px] uppercase tracking-wide text-danger">
                      failed
                    </span>
                  ) : null}
                </div>
                <div className="mt-1 flex items-center gap-2 text-[11px] text-fg-subtle">
                  <span>{formatSidebarTime(item.createdAt)}</span>
                  {item.conversationType ? (
                    <span className="text-fg-muted">
                      · {item.conversationType.replace(/_/g, " ")}
                    </span>
                  ) : null}
                </div>
                {item.sentiment ? (
                  <div className="mt-1.5">
                    <span
                      className={`inline-block text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded border ${sentimentClasses(
                        item.sentiment
                      )}`}
                    >
                      {item.sentiment}
                    </span>
                  </div>
                ) : null}
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}
