/* Layout primitives: page heading, cards, key/value lists, notes. */
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

export function PageHead({ title, sub, actions, eyebrow, back }: { title: ReactNode; sub?: ReactNode; actions?: ReactNode; eyebrow?: ReactNode; back?: { to: string; label: string } }) {
  return (
    <div>
      {back && (
        <Link className="back" to={back.to}>
          ← {back.label}
        </Link>
      )}
      <div className="page-head">
        <div>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h1>{title}</h1>
          {sub && <p>{sub}</p>}
        </div>
        {actions && <div className="actions">{actions}</div>}
      </div>
    </div>
  );
}

/** A card with a padded body. Use `flush` for tables that should sit edge to edge. */
export function Card({ title, sub, actions, flush, className, children }: { title: ReactNode; sub?: ReactNode; actions?: ReactNode; flush?: boolean; className?: string; children: ReactNode }) {
  return (
    <section className={'card' + (className ? ' ' + className : '')}>
      <header>
        <div style={{ minWidth: 0 }}>
          <h3>{title}</h3>
          {sub && <p>{sub}</p>}
        </div>
        {actions && <div className="actions">{actions}</div>}
      </header>
      {flush ? children : <div className="body">{children}</div>}
    </section>
  );
}

export type KVRow = [string, ReactNode] | null | false | undefined;

const empty = (v: ReactNode) => v === null || v === undefined || v === '' || v === false;

export function KV({ rows }: { rows: KVRow[] }) {
  return (
    <dl className="kv">
      {rows.filter((r): r is [string, ReactNode] => !!r).map(([k, v]) => (
        <div key={k} style={{ display: 'contents' }}>
          <dt>{k}</dt>
          <dd>{empty(v) ? '—' : v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Note({ title, children, meta, actions }: { title: ReactNode; children?: ReactNode; meta?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="note">
      <b>{title}</b>
      {children && <> — {children}</>}
      {meta && <small>{meta}</small>}
      {actions && <div className="inline-actions">{actions}</div>}
    </div>
  );
}

export function Muted({ children }: { children: ReactNode }) {
  return <p className="muted">{children}</p>;
}
