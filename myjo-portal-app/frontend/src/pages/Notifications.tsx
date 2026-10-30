/* Notifications log (GET /notifications?limit=150) and "Send due reminders" (POST /reminders/run). */
import { asList, post, toApiError } from '../api';
import { fdt, plural } from '../format';
import { useApi } from '../hooks';
import type { ListResponse, NotificationEntry } from '../types';
import { Async } from '../ui/Async';
import { PageHead } from '../ui/Card';
import { Pill } from '../ui/Pill';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

export default function Notifications() {
  const st = useApi<ListResponse<NotificationEntry>>('/notifications', { limit: 150 });
  const toast = useToast();
  const run = async () => {
    try {
      const r = await post<{ sent: number }>('/reminders/run');
      toast(r.sent ? plural(r.sent, 'reminder') + ' sent' : 'No reminders due right now');
      st.reload();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };
  return (
    <>
      <PageHead
        title="Notifications"
        sub="Email and WhatsApp messages the portal has sent or logged. When sending is switched off on the server, messages are logged only."
        actions={<button type="button" className="btn primary" onClick={() => void run()}>Send due reminders</button>}
      />
      <Async state={st}>
        {(d) => (
          <Table
            columns={[
              { label: 'When', render: (n) => <span className="mono">{fdt(n.at)}</span> },
              { label: 'Event', render: (n) => <><b>{n.event}</b>{n.ref && <span className="sub mono">{n.ref}</span>}</> },
              {
                label: 'Recipients', w: true,
                render: (n) => (n.recipients.length ? n.recipients.map((t, i) => <span key={i} style={{ display: 'block' }}>{t.name}<span className="sub">{[t.email, t.phone].filter(Boolean).join(' · ')}</span></span>) : '—'),
              },
              { label: 'Message', w: true, render: (n) => n.message },
              { label: 'Channels', render: (n) => n.channel },
              { label: 'Status', render: (n) => <Pill s={n.status} tone={/^sent/i.test(n.status) ? 'good' : /^fail/i.test(n.status) ? 'bad' : /^queued/i.test(n.status) ? 'warn' : 'neutral'} /> },
            ]}
            rows={asList(d)}
            rowKey={(_, i) => i}
            empty="No notifications yet."
          />
        )}
      </Async>
    </>
  );
}
