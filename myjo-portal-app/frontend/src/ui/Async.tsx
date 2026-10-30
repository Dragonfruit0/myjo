/* Loading and error states for data fetched with useApi. */
import type { ReactNode } from 'react';
import type { Loadable } from '../hooks';

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="loading" role="status">
      {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="err-card" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="btn sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

/** Renders children with the data once loaded; shows loading/error states otherwise. */
export function Async<T>({ state, children }: { state: Loadable<T>; children: (data: T) => ReactNode }) {
  if (state.error && !state.data) return <ErrorBox message={state.error.message} onRetry={state.reload} />;
  if (!state.data) return <Loading />;
  return (
    <>
      {state.error && <ErrorBox message={state.error.message} onRetry={state.reload} />}
      {children(state.data)}
    </>
  );
}
