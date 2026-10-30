/* Dated work list used on the dashboard (overdue, coming up, my work). */
import { Link } from 'react-router-dom';
import { daysBetween, fd, timeOf, today } from '../format';
import { linkPath } from '../nav';
import type { DashItem } from '../types';
import { Muted } from './Card';

export function ItemList({ items, late, empty }: { items: DashItem[]; late?: boolean; empty: string }) {
  if (!items.length) return <Muted>{empty}</Muted>;
  return (
    <div className="list">
      {items.map((x, i) => {
        const isLate = late || x.late;
        return (
          <Link className="li go" key={i} to={linkPath(x.link)}>
            <span className={'when' + (isLate ? ' late' : '')}>{fd(x.date)}</span>
            <div className="t">
              <b>{x.title}</b>
              <span>{x.subtitle}</span>
            </div>
            <span>{isLate ? <span className="pill bad">{daysBetween(x.date, today())}d late</span> : <span className="muted mono">{timeOf(x.date)}</span>}</span>
          </Link>
        );
      })}
    </div>
  );
}
