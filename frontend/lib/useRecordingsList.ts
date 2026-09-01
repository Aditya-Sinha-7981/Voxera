"use client";

/**
 * Loads the recordings list (sidebar) and refreshes on demand.
 * Surfaces a single `items` array; `loading` and `error` are orthogonal.
 */

import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { RecordingListItem } from "@/lib/types";

const DEFAULT_LIMIT = 50;

type State = {
  items: RecordingListItem[];
  loading: boolean;
  error: ApiError | null;
};

export function useRecordingsList(): State & { refresh: () => Promise<void> } {
  const [state, setState] = useState<State>({
    items: [],
    loading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const response = await api.listRecordings({ limit: DEFAULT_LIMIT });
      setState({ items: response.items, loading: false, error: null });
    } catch (err) {
      const apiErr =
        err instanceof ApiError
          ? err
          : new ApiError(0, "NETWORK_ERROR", "Could not reach the backend.");
      setState({ items: [], loading: false, error: apiErr });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { ...state, refresh };
}
