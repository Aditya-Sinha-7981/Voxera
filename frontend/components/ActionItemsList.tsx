"use client";

import { priorityClasses } from "@/lib/format";
import type { ActionItem } from "@/lib/types";

export function ActionItemsList({ items }: { items: ActionItem[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-fg-subtle italic">No action items.</p>
    );
  }
  return (
    <ul className="space-y-2">
      {items.map((item, idx) => (
        <li
          key={`${item.action}-${idx}`}
          className="border border-border rounded-md bg-bg-soft px-3 py-2"
        >
          <div className="text-sm text-fg">{item.action}</div>
          <div className="mt-1.5 flex flex-wrap gap-1.5 text-[11px]">
            {item.department ? (
              <span className="px-1.5 py-0.5 rounded border border-border-soft text-fg-muted">
                {item.department}
              </span>
            ) : null}
            <span
              className={`px-1.5 py-0.5 rounded border uppercase tracking-wide ${priorityClasses(
                item.priority
              )}`}
            >
              {item.priority}
            </span>
            <span className="px-1.5 py-0.5 rounded border border-border-soft text-fg-muted">
              {item.status}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
