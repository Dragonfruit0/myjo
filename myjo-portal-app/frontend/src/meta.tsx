/* Lookup lists from GET /meta (classes, subjects, series, people …), loaded once after sign-in. */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { get, toApiError, type ApiError } from './api';
import type { Meta } from './types';

interface MetaValue {
  meta: Meta | null;
  error: ApiError | null;
  reload: () => void;
}

const MetaContext = createContext<MetaValue | null>(null);

function normalize(raw: Partial<Meta>): Meta {
  const a = <T,>(x: T[] | undefined): T[] => (Array.isArray(x) ? x : []);
  return {
    classes: a(raw.classes),
    subjects: a(raw.subjects),
    series: a(raw.series),
    all_series_colors: raw.all_series_colors ?? {},
    academic_years: a(raw.academic_years),
    boards: a(raw.boards),
    request_statuses: a(raw.request_statuses),
    order_statuses: a(raw.order_statuses),
    confirmed_statuses: raw.confirmed_statuses?.length ? raw.confirmed_statuses : ['Order Confirmed', 'Partially Confirmed'],
    training_statuses: a(raw.training_statuses),
    paper_statuses: a(raw.paper_statuses),
    resource_statuses: a(raw.resource_statuses),
    exam_types: a(raw.exam_types),
    resource_types: a(raw.resource_types),
    training_types: a(raw.training_types),
    followup_methods: a(raw.followup_methods),
    payment_statuses: a(raw.payment_statuses),
    discussion_stages: a(raw.discussion_stages),
    requested_items: a(raw.requested_items),
    interest_levels: a(raw.interest_levels),
    access_levels: a(raw.access_levels),
    people: { demo: a(raw.people?.demo), mkt: a(raw.people?.mkt), acad: a(raw.people?.acad) },
    distributors: a(raw.distributors),
    role_labels: raw.role_labels ?? {},
  };
}

export function MetaProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setMeta(null);
      return undefined;
    }
    let live = true;
    setError(null);
    get<Partial<Meta>>('/meta')
      .then((m) => live && setMeta(normalize(m)))
      .catch((e: unknown) => live && setError(toApiError(e)));
    return () => {
      live = false;
    };
  }, [enabled, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return <MetaContext.Provider value={{ meta, error, reload }}>{children}</MetaContext.Provider>;
}

export function useMetaState(): MetaValue {
  const v = useContext(MetaContext);
  if (!v) throw new Error('useMeta must be used inside <MetaProvider>');
  return v;
}

/** Inside the signed-in shell meta is always loaded (the shell waits for it). */
export function useMeta(): Meta {
  const { meta } = useMetaState();
  if (!meta) throw new Error('Meta not loaded');
  return meta;
}
