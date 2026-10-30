/* Dashboard (GET /dashboard): grouped KPIs, overdue, coming up, My work, downloads, funnel, cancellations. */
import { asList, post, toApiError } from '../api';
import { useAuth, useUser } from '../auth';
import { useDistOrders } from '../forms/useDistOrders';
import { useRequestForm } from '../forms/useRequestForm';
import { fd, fdt, plural, today } from '../format';
import { useApi } from '../hooks';
import { requestPath } from '../nav';
import type { Dashboard as DashboardData, ListResponse, PendingCancellation, RequestListItem } from '../types';
import { Async } from '../ui/Async';
import { Card, Muted, Note, PageHead } from '../ui/Card';
import { ItemList } from '../ui/ItemList';
import { KpiGroups } from '../ui/Kpi';
import { useModal } from '../ui/Modal';
import { Pill } from '../ui/Pill';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';
import { Link } from 'react-router-dom';

function Cancellations({ items, onDone }: { items: PendingCancellation[]; onDone: () => void }) {
  const toast = useToast();
  const modal = useModal();
  const decide = async (x: PendingCancellation, verb: 'approve' | 'decline') => {
    try {
      await post(`/cancellations/${x.entity}/${x.id}/${verb}`);
      toast(verb === 'approve' ? 'Cancelled · record kept for audit' : 'Cancellation declined');
      onDone();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };
  const approve = (x: PendingCancellation) =>
    modal.open({
      title: 'Approve cancellation',
      sub: `${x.label} · ${x.ref} · ${x.name}`,
      render: (close) => (
        <>
          <p>Records are never deleted. The record is marked cancelled and kept for audit.</p>
          <div className="mfoot">
            <button type="button" className="btn" onClick={close}>
              Back
            </button>
            <button type="button" className="btn danger" onClick={() => { close(); void decide(x, 'approve'); }}>
              Approve cancellation
            </button>
          </div>
        </>
      ),
    });
  return (
    <Card title="Cancellations awaiting your approval">
      {items.map((x) => (
        <Note
          key={x.entity + x.id}
          title={`${x.label} · ${x.ref} · ${x.name}`}
          meta={`Requested by ${x.by} on ${fdt(x.at)}`}
          actions={
            <>
              <button type="button" className="btn sm danger" onClick={() => approve(x)}>
                Approve cancellation
              </button>
              <button type="button" className="btn sm" onClick={() => void decide(x, 'decline')}>
                Keep record
              </button>
            </>
          }
        >
          {x.reason}
        </Note>
      ))}
    </Card>
  );
}

function Funnel({ data }: { data: DashboardData }) {
  const max = Math.max(1, ...data.funnel.map((f) => f.value));
  return (
    <Card title="Pipeline funnel">
      <div className="bars">
        {data.funnel.map((f) => (
          <div className="bar" key={f.label}>
            <span>{f.label}</span>
            <span className="tr" aria-hidden="true">
              <span style={{ width: `${(f.value / max) * 100}%` }} />
            </span>
            <span className="c">{f.value}</span>
          </div>
        ))}
      </div>
      <div>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          Converted schools with no downloads
        </div>
        {data.no_download_schools.length ? (
          <div className="tags">
            {data.no_download_schools.map((n) => (
              <span className="tag" key={n}>
                {n}
              </span>
            ))}
          </div>
        ) : (
          <Muted>Every converted school has downloaded at least once.</Muted>
        )}
      </div>
    </Card>
  );
}

function LatestRequests() {
  const st = useApi<RequestListItem[] | ListResponse<RequestListItem>>('/requests');
  const rows = asList(st.data).slice().sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 6);
  return (
    <Card title="Latest requests" flush>
      <Table
        columns={[
          { label: 'Request', render: (r) => <span className="mono">{r.no}</span> },
          { label: 'School', render: (r) => r.school.name },
          { label: 'Status', render: (r) => <Pill s={r.cancelled ? 'Cancelled' : r.status} /> },
        ]}
        rows={rows}
        rowKey={(r) => String(r.id)}
        rowTo={(r) => requestPath(r.id)}
        empty={st.loading ? 'Loading…' : 'No demo requests yet.'}
      />
    </Card>
  );
}

export default function Dashboard() {
  const user = useUser();
  const { can, sees } = useAuth();
  const st = useApi<DashboardData>('/dashboard');
  const toast = useToast();
  const openRequest = useRequestForm();
  const { createOrder } = useDistOrders();
  const isDist = user.role === 'dist';

  const runReminders = async () => {
    try {
      const r = await post<{ sent: number }>('/reminders/run');
      toast(r.sent ? plural(r.sent, 'reminder') + ' sent' : 'No reminders due right now');
      st.reload();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };

  const actions = (
    <>
      {isDist && can('placeOrder') && (
        <button type="button" className="btn primary" onClick={() => void createOrder(st.reload)}>
          Create order
        </button>
      )}
      {can('createRequest') && (
        <button type="button" className={'btn' + (isDist && !can('placeOrder') ? ' primary' : '')} onClick={() => openRequest(null)}>
          New demo request
        </button>
      )}
      {!isDist && sees('notifications') && (
        <button type="button" className="btn" onClick={() => void runReminders()}>
          Send due reminders
        </button>
      )}
    </>
  );

  return (
    <>
      <PageHead
        title={isDist ? 'Welcome, ' + user.name : 'Dashboard'}
        sub={isDist ? 'Your schools, demo status and order status.' : `School journey from distributor request to academic support, as of ${fd(today())}.`}
        actions={actions}
      />
      <Async state={st}>
        {(d) => (
          <>
            {d.my_work.length > 0 && (
              <Card title="My work" sub={`${user.role_label} · ${user.name}`}>
                {d.my_work.some((g) => g.items.length) ? (
                  d.my_work
                    .filter((g) => g.items.length)
                    .map((g) => (
                      <div className="wg" key={g.title}>
                        <div className="eyebrow">
                          {g.title} · {g.items.length}
                        </div>
                        <ItemList items={g.items} empty="" />
                      </div>
                    ))
                ) : (
                  <Muted>You’re all caught up.</Muted>
                )}
              </Card>
            )}
            {can('approveCancel') && d.pending_cancellations.length > 0 && <Cancellations items={d.pending_cancellations} onDone={st.reload} />}
            <KpiGroups kpis={d.kpis} />
            {isDist ? (
              <div className="grid2">
                <Card title="Upcoming demos">
                  <ItemList items={d.upcoming} empty="No demos scheduled in the next 30 days." />
                </Card>
                <LatestRequests />
              </div>
            ) : (
              <>
                <div className="grid2">
                  <Card title="Overdue" sub={`${plural(d.overdue.length, 'item')} past their due date`}>
                    <ItemList items={d.overdue} late empty="Nothing overdue." />
                  </Card>
                  <Card title="Coming up · next 3 weeks" sub="Demos, trainings, follow-ups and question-paper due dates">
                    <ItemList items={d.upcoming} empty="Nothing scheduled in the next three weeks." />
                  </Card>
                </div>
                <div className="grid2">
                  <Card title="Downloads by school" flush actions={sees('downloads') ? <Link className="btn" to="/downloads">Open log</Link> : undefined}>
                    <Table
                      columns={[
                        { label: 'School', render: (x) => x.school },
                        { label: 'Question papers & keys', n: true, render: (x) => x.papers },
                        { label: 'Manuals & resources', n: true, render: (x) => x.resources },
                        { label: 'Last download', render: (x) => (x.last ? fdt(x.last) : <Pill s="No downloads" />) },
                      ]}
                      rows={d.downloads_by_school.slice().sort((a, b) => b.papers + b.resources - (a.papers + a.resources))}
                      rowKey={(x) => String(x.request_id)}
                    />
                  </Card>
                  {d.funnel.length > 0 && <Funnel data={d} />}
                </div>
              </>
            )}
          </>
        )}
      </Async>
    </>
  );
}
