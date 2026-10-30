/*
 * Data table inside its own horizontal scroller (so the page never scrolls sideways on a phone).
 * With `rowTo`, the first cell becomes a link and the whole row is clickable with the mouse;
 * keyboard users tab to the link.
 */
import type { MouseEvent, ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export interface Column<T> {
  label: string;
  /** right-aligned numeric column */
  n?: boolean;
  /** wrapping (wide text) column */
  w?: boolean;
  render: (row: T) => ReactNode;
}

interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, i: number) => string | number;
  empty?: string;
  rowTo?: (row: T) => string | null;
  total?: ReactNode[];
  caption?: string;
}

export function Table<T>({ columns, rows, rowKey, empty = 'Nothing to show yet.', rowTo, total, caption }: TableProps<T>) {
  const navigate = useNavigate();
  if (!rows.length) {
    return (
      <div className="tw">
        <div className="empty">{empty}</div>
      </div>
    );
  }
  const onRowClick = (to: string | null) => (e: MouseEvent<HTMLTableRowElement>) => {
    if (!to) return;
    const t = e.target as HTMLElement;
    if (t.closest('a,button,input,select,textarea,label')) return;
    navigate(to);
  };
  const cls = (c: Column<T>) => [c.n ? 'n' : '', c.w ? 'w' : ''].filter(Boolean).join(' ') || undefined;
  return (
    <div className="tw">
      <table>
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((c, i) => (
              <th key={i} scope="col" className={c.n ? 'n' : undefined}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const to = rowTo ? rowTo(r) : null;
            return (
              <tr key={rowKey(r, i)} className={to ? 'click' : undefined} onClick={to ? onRowClick(to) : undefined}>
                {columns.map((c, ci) => (
                  <td key={ci} className={cls(c)}>
                    {ci === 0 && to ? <Link to={to}>{c.render(r)}</Link> : c.render(r)}
                  </td>
                ))}
              </tr>
            );
          })}
          {total && (
            <tr className="total">
              {total.map((v, i) => (
                <td key={i} className={columns[i]?.n ? 'n' : undefined}>
                  {v}
                </td>
              ))}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
