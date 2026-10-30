/* Distributor › My orders (GET /my-orders) with the Create order flow. */
import { get, toApiError } from '../api';
import { useAuth } from '../auth';
import { useDistOrders } from '../forms/useDistOrders';
import { fd, num } from '../format';
import { useApi } from '../hooks';
import { requestPath } from '../nav';
import type { CanOrderRow, MyOrders, RequestDetail } from '../types';
import { Async } from '../ui/Async';
import { Card, PageHead } from '../ui/Card';
import { Kpi } from '../ui/Kpi';
import { Pill } from '../ui/Pill';
import { SeriesTags } from '../ui/Tags';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

export default function MyOrdersPage() {
  const { can } = useAuth();
  const st = useApi<MyOrders>('/my-orders');
  const dist = useDistOrders();
  const toast = useToast();
  // `final_orders` mirrors the directConfirm permission on the server.
  const direct = st.data?.final_orders ?? can('directConfirm');

  const orderFor = async (row: CanOrderRow) => {
    try {
      const r = await get<RequestDetail>(`/requests/${row.id}`);
      if (r.actions.includes('dist_order') || r.actions.includes('dist_confirm')) dist.orderFor(r, st.reload);
      else toast('An order cannot be placed for this school right now.', 'bad');
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };

  const rowLabel = (row: CanOrderRow) => (direct ? (row.dist_order_status === 'Submitted' ? 'Confirm order' : 'Create order') : row.dist_order_status ? 'Update & resubmit' : 'Place order');

  return (
    <>
      <PageHead
        title="My orders"
        sub={direct ? 'Create book orders for your schools or a new school. Orders you create are final; no Myjo approval is needed.' : 'Place book orders for your schools or a new school. Myjo Marketing confirms each order.'}
        actions={
          can('placeOrder') && (
            <button type="button" className="btn primary" onClick={() => void dist.createOrder(st.reload)}>
              Create order
            </button>
          )
        }
      />
      <Async state={st}>
        {(d) => (
          <>
            <div className="kpis">
              <Kpi value={d.kpis.waiting} label="Waiting for Myjo" />
              <Kpi value={d.kpis.returned} label="Returned for changes" tone={d.kpis.returned ? 'alert' : undefined} />
              <Kpi value={d.kpis.confirmed} label="Confirmed schools" tone="hl" />
              <Kpi value={d.kpis.books} label="Books confirmed" />
            </div>
            <Card title="Schools you can order for" sub="Any of your schools without a confirmed or waiting order" flush>
              <Table
                columns={[
                  { label: 'School', render: (r) => r.school },
                  { label: 'City', render: (r) => r.city },
                  { label: 'Status', render: (r) => <Pill s={r.status} /> },
                  { label: 'Order', render: (r) => (r.dist_order_status ? <><Pill s={r.dist_order_status} />{r.review_note && <span className="sub">{r.review_note}</span>}</> : <span className="muted">Not placed</span>) },
                  {
                    label: 'Action',
                    render: (r) =>
                      can('placeOrder') && (
                        <button type="button" className="btn sm primary" onClick={() => void orderFor(r)}>
                          {rowLabel(r)}
                        </button>
                      ),
                  },
                ]}
                rows={d.can_order}
                rowKey={(r) => String(r.id)}
                empty="No schools to order for. Use Create order to add a new school."
              />
            </Card>
            <Card title="Orders placed & confirmed" flush>
              <Table
                columns={[
                  { label: 'School', render: (r) => r.school },
                  { label: 'PO / ref', render: (r) => <span className="mono">{r.po}</span> },
                  { label: 'Series', render: (r) => <SeriesTags names={r.series} /> },
                  { label: 'Qty', n: true, render: (r) => num(r.qty) },
                  { label: 'Placed', render: (r) => (r.by_myjo ? <span className="muted">By Myjo</span> : fd(r.placed)) },
                  { label: 'Status', render: (r) => <Pill s={r.status} /> },
                  { label: 'Expected delivery', render: (r) => fd(r.delivery) },
                ]}
                rows={d.orders}
                rowKey={(r) => String(r.id)}
                rowTo={(r) => requestPath(r.id)}
                empty="No orders yet."
              />
            </Card>
          </>
        )}
      </Async>
    </>
  );
}
