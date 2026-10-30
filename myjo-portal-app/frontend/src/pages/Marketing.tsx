/* Marketing & follow-ups: open schools after the demo (GET /marketing) and recent follow-ups (GET /followups). */
import { asList } from '../api';
import { fd, fdt, num } from '../format';
import { useApi } from '../hooks';
import { requestPath } from '../nav';
import type { Followup, ListResponse, MarketingRow } from '../types';
import { Async } from '../ui/Async';
import { Card, PageHead } from '../ui/Card';
import { Pill } from '../ui/Pill';
import { Table } from '../ui/Table';

export default function Marketing() {
  const open = useApi<ListResponse<MarketingRow>>('/marketing');
  const fus = useApi<ListResponse<Followup>>('/followups', { limit: 25 });

  return (
    <>
      <PageHead title="Marketing & follow-ups" sub="Schools after the demo, sorted by next follow-up. Overdue dates are red." />
      <Async state={open}>
        {(d) => {
          const rows = asList(d);
          return (
            <Card title="Open follow-ups" sub={`${rows.length} schools`} flush>
              <Table
                columns={[
                  { label: 'School', render: (r) => <>{r.school.name}<span className="sub">{r.school.city} · {r.distributor.name}</span></> },
                  { label: 'Potential', render: (r) => <Pill s={r.potential} /> },
                  { label: 'Stage', render: (r) => r.stage || 'Awaiting marketing feedback' },
                  { label: 'Order status', render: (r) => <>{<Pill s={r.order_status} />}{r.dist_order_status && <span className="sub">Distributor order: {r.dist_order_status}</span>}</> },
                  { label: 'Expected qty', n: true, render: (r) => num(r.exp_qty) },
                  { label: 'Next action', render: (r) => r.next_action || '—' },
                  { label: 'Next follow-up', render: (r) => (r.next_follow ? <span className={r.overdue ? 'late' : undefined}>{fd(r.next_follow)}</span> : '—') },
                  { label: 'Marketing person', render: (r) => r.person || '—' },
                ]}
                rows={rows}
                rowKey={(r) => String(r.id)}
                rowTo={(r) => requestPath(r.id)}
                empty="No schools are waiting for follow-up."
              />
            </Card>
          );
        }}
      </Async>
      <Async state={fus}>
        {(d) => (
          <Card title="Follow-up history" sub="Latest 25 entries across all schools" flush>
            <Table
              columns={[
                { label: 'Date & time', render: (f) => <span className="mono">{fdt(f.at)}</span> },
                { label: 'School', render: (f) => f.school || '—' },
                { label: 'Method', render: (f) => f.method },
                { label: 'Person contacted', render: (f) => f.person },
                { label: 'Summary', w: true, render: (f) => f.summary },
                { label: 'Next action', render: (f) => f.next_action || '—' },
                { label: 'Next date', render: (f) => fd(f.next_date) },
                { label: 'Updated by', render: (f) => f.by },
              ]}
              rows={asList(d)}
              rowKey={(f) => String(f.id)}
              rowTo={(f) => (f.request_id !== undefined ? requestPath(f.request_id) : null)}
              empty="No follow-ups logged yet."
            />
          </Card>
        )}
      </Async>
    </>
  );
}
