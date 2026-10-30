/* Demo requests list (GET /requests?q=&status=). */
import { useState } from 'react';
import { asList } from '../api';
import { useAuth } from '../auth';
import { useRequestForm } from '../forms/useRequestForm';
import { fd } from '../format';
import { useApi, useDebounced } from '../hooks';
import { useMeta } from '../meta';
import { requestPath } from '../nav';
import type { ListResponse, RequestListItem } from '../types';
import { Async } from '../ui/Async';
import { PageHead } from '../ui/Card';
import { Pill, StatusPills } from '../ui/Pill';
import { Table, type Column } from '../ui/Table';

export const requestColumns: Column<RequestListItem>[] = [
  { label: 'Request no.', render: (r) => (<><span className="mono">{r.no}</span><span className="sub">{fd(r.created_at)}</span></>) },
  { label: 'School', render: (r) => (<>{r.school.name}<span className="sub">{r.school.board} · AY {r.ay}</span></>) },
  { label: 'City', render: (r) => (<>{r.school.city}<span className="sub">{r.school.state}</span></>) },
  { label: 'Distributor', render: (r) => r.distributor?.name ?? '—' },
  { label: 'Preferred demo', render: (r) => (r.pref_date ? <>{fd(r.pref_date)} <span className="muted">{r.pref_time}</span></> : '—') },
  { label: 'Assigned', render: (r) => r.assigned_to || '—' },
  { label: 'Status', render: (r) => <StatusPills status={r.status} cancelled={r.cancelled} cancelPending={r.cancel_pending} /> },
  { label: 'Order status', render: (r) => <Pill s={r.order_status} /> },
];

export function RequestTable({ rows, empty = 'No demo requests match.' }: { rows: RequestListItem[]; empty?: string }) {
  return <Table columns={requestColumns} rows={rows} rowKey={(r) => String(r.id)} rowTo={(r) => requestPath(r.id)} empty={empty} />;
}

export default function Requests() {
  const meta = useMeta();
  const { can, user } = useAuth();
  const openRequest = useRequestForm();
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const dq = useDebounced(q);
  const st = useApi<RequestListItem[] | ListResponse<RequestListItem>>('/requests', { q: dq, status });

  return (
    <>
      <PageHead
        title="Demo requests"
        sub={user?.role === 'dist' ? 'Requests you have submitted for your schools.' : 'Review every distributor request, schedule demos and track each school to conversion.'}
        actions={
          can('createRequest') && (
            <button type="button" className="btn primary" onClick={() => openRequest(null)}>
              New demo request
            </button>
          )
        }
      />
      <div className="filters">
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search school, city, request no., mobile…" aria-label="Search requests" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">All statuses</option>
          {meta.request_statuses.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      <Async state={st}>
        {(d) => {
          const rows = asList(d);
          return (
            <div className="stack" style={{ gap: 8 }}>
              <p className="muted" aria-live="polite">
                {rows.length} request{rows.length === 1 ? '' : 's'}
              </p>
              <RequestTable rows={rows} />
            </div>
          );
        }}
      </Async>
    </>
  );
}
