import { useCallback, useEffect, useState } from 'react';
import { ApiError, get, qs, toApiError, type Query } from './api';

export interface Loadable<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => void;
}

/**
 * GETs `path` (with optional query) and reloads whenever either changes.
 * Pass `null` to skip. Previous data is kept while a reload is in flight to avoid flicker.
 */
export function useApi<T>(path: string | null, query?: Query): Loadable<T> {
  const key = path === null ? null : path + qs(query);
  const [tick, setTick] = useState(0);
  const [state, setState] = useState<{ data: T | null; error: ApiError | null; loading: boolean }>({
    data: null,
    error: null,
    loading: key !== null,
  });

  useEffect(() => {
    if (key === null || path === null) return undefined;
    let live = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    get<T>(path, query)
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((e: unknown) => live && setState((s) => ({ data: s.data, error: toApiError(e), loading: false })));
    return () => {
      live = false;
    };
    // `key` captures path + query; listing `query` would re-run on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}

/** Returns `value` after it has stopped changing for `ms`. */
export function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const h = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(h);
  }, [value, ms]);
  return v;
}
