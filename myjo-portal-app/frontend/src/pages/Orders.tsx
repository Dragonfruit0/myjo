/* Book orders (GET /orders): distributor orders awaiting review, totals and confirmed orders. */
import { useAuth } from '../auth';
import { fd, fdt, list, num } from '../format';
import { useApi } from '../hooks';
import { useMeta } from '../meta';
import { requestPath } from '../nav';
import type { OrdersOverview } from '../types';
import { Async } from '../ui/Async';
import { Card, PageHead } from '../ui/Card';
import { Kpi } from '../ui/Kpi';
import { Pill } from '../ui/Pill';
import { SeriesTags } from '../ui/Tags';
import { Table } from '../ui/Table';

export default function Orders() {
  const { can, sees } = useAuth();
  const meta = useMeta();
  const st = useApi<OrdersOverview>('/orders');
  return (
    <>
      <PageHead title="Book orders" sub="Whether each school has purchased from Myjo, and the confirmed order details." />
      <Async state={st}>
        {(d) => (
          <>
            {(d.pending_dist.length > 0 || can('order')) && (
              <Card title="Orders placed by distributors · awaiting review" sub="Open a school to accept, return or reject" flush>
                <Table
                  columns={[
                    { label: 'School', render: (r) => r.school },
                    { label: 'Distributor', render: (r) => r.distributor },
                    { label: 'PO / ref', render: (r) => <span className="mono">{r.po}</span> },
                    { label: 'Series', render: (r) => <SeriesTags names={r.series} /> },
                    { label: 'Qty', n: true, render: (r) => num(r.qty) },
                    { label: 'Placed', render: (r) => fdt(r.at) },
                    { label: 'Required by', render: (r) => fd(r.req_delivery) },
                  ]}
                  rows={d.pending_dist}
                  rowKey={(r) => String(r.request_id)}
                  rowTo={(r) => requestPath(r.request_id)}
                  empty="No distributor orders waiting."
                />
              </Card>
            )}
            <div className="kpis">
              <Kpi value={d.totals.schools} label="Converted schools" tone="hl" />
              <Kpi value={d.totals.books} label="Books ordered" />
              {Object.entries(d.status_counts)
                .filter(([s]) => !meta.confirmed_statuses.includes(s))
                .map(([s, n]) => (
                  <Kpi key={s} value={n} label={s} link={sees('marketing') ? 'marketing' : undefined} />
                ))}
            </div>
            <Card title="Confirmed orders" flush>
              <Table
                columns={[
                  { label: 'School', render: (r) => <>{r.school}<span className="sub">{r.city} · <Pill s={r.order_status} /></span></> },
                  { label: 'AY', render: (r) => r.ay },
                  { label: 'Distributor', render: (r) => r.distributor },
                  { label: 'Series', render: (r) => <SeriesTags names={r.series} /> },
                  { label: 'Classes · subjects', w: true, render: (r) => `${list(r.classes)} · ${list(r.subjects)}` },
                  { label: 'Qty', n: true, render: (r) => num(r.qty) },
                  { label: 'PO / ref', render: (r) => <span className="mono">{r.po}</span> },
                  { label: 'Confirmed', render: (r) => fd(r.conf_date) },
                  { label: 'Delivery', render: (r) => fd(r.del_date) },
                  { label: 'Payment', render: (r) => <Pill s={r.payment} /> },
                ]}
                rows={d.confirmed}
                rowKey={(r) => String(r.request_id)}
                rowTo={(r) => requestPath(r.request_id)}
                total={d.confirmed.length ? ['Total', '', '', '', '', num(d.totals.books), '', '', '', ''] : undefined}
                empty="No confirmed orders yet."
              />
            </Card>
          </>
        )}
      </Async>
    </>
  );
}
