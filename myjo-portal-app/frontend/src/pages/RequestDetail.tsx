/* Request detail (GET /requests/<id>): progress, all workflow cards and the actions the server allows. */
import { useParams } from 'react-router-dom';
import { useAuth } from '../auth';
import { usePaperForm, useTrainingForm } from '../forms/academicForms';
import { fdt } from '../format';
import { useApi } from '../hooks';
import type { RequestDetail } from '../types';
import { Async } from '../ui/Async';
import { Card, Note, PageHead } from '../ui/Card';
import { Pill } from '../ui/Pill';
import { AcademicCard, AuditCard, DistOrderCard, FeedbackCard, MarketingCard, NotesCard, OrderCard, PackCard, SchoolCard, ScheduleCard, Steps } from './request/cards';
import { ActionButtons, useRequestActions, type ActionButton } from './request/useRequestActions';

function Detail({ r, reload }: { r: RequestDetail; reload: () => void }) {
  const { can } = useAuth();
  const { top, handlers, has, confirmed } = useRequestActions(r, reload);
  const openTraining = useTrainingForm();
  const openPaper = usePaperForm();

  const scheduleButtons: ActionButton[] = [];
  if (has('share')) scheduleButtons.push({ code: 'share', label: r.schedule?.shared_at ? 'Share again' : 'Share details', tone: r.schedule?.shared_at ? undefined : 'primary', run: handlers.share });
  if (has('schedule') && r.schedule) scheduleButtons.push({ code: 'schedule', label: 'Reschedule', run: handlers.schedule });

  const feedbackButtons: ActionButton[] = has('feedback') && r.feedback ? [{ code: 'feedback', label: 'Edit', run: handlers.feedback }] : [];

  const distButtons: ActionButton[] = [];
  if (has('accept_dist')) distButtons.push({ code: 'accept_dist', label: 'Accept & confirm order', tone: 'primary', run: handlers.accept_dist });
  if (has('return_dist')) distButtons.push({ code: 'return_dist', label: 'Return for changes', run: handlers.return_dist });
  if (has('reject_dist')) distButtons.push({ code: 'reject_dist', label: 'Reject', tone: 'danger', run: handlers.reject_dist });

  const academicActions = can('academic') && !r.cancelled ? (
    <>
      <button type="button" className="btn sm" onClick={() => void openTraining({ preselect: r.id, onSaved: reload })}>
        New group training
      </button>
      <button type="button" className="btn sm" onClick={() => void openPaper({ preselect: r.id, onSaved: reload })}>
        New question paper
      </button>
    </>
  ) : undefined;

  return (
    <>
      <PageHead
        back={{ to: '/requests', label: 'Demo requests' }}
        eyebrow={<span className="mono">{r.no}</span>}
        title={r.school.name}
        sub={
          <>
            {r.school.city}, {r.school.state} · {r.school.board} · AY {r.ay} · <Pill s={r.cancelled ? 'Cancelled' : r.status} /> {r.order_status && <Pill s={r.order_status} />}
            {r.cancel && !r.cancelled && <> <Pill s="Cancellation pending" /></>}
          </>
        }
      />
      {r.cancelled && r.cancel && (
        <Note title="Cancelled" meta={`Requested by ${r.cancel.by} · ${fdt(r.cancel.at)}${r.cancel.approved_by ? ' · approved by ' + r.cancel.approved_by : ''}`}>
          {r.cancel.reason}
        </Note>
      )}
      {top.length > 0 && (
        <div className="actions">
          <ActionButtons buttons={top} />
        </div>
      )}
      <Card title="Progress">
        <Steps r={r} />
      </Card>
      <div className="grid2">
        <div className="stack">
          <SchoolCard r={r} />
          <NotesCard r={r} />
          <DistOrderCard r={r} buttons={distButtons} />
          <PackCard r={r} />
          <OrderCard r={r} confirmed={confirmed} />
        </div>
        <div className="stack">
          <ScheduleCard r={r} buttons={scheduleButtons} />
          <FeedbackCard r={r} buttons={feedbackButtons} />
          <MarketingCard r={r} />
          <AcademicCard r={r} actions={academicActions} />
        </div>
      </div>
      {r.audit && r.audit.length > 0 && <AuditCard entries={r.audit} />}
    </>
  );
}

export default function RequestDetailPage() {
  const { id = '' } = useParams();
  const st = useApi<RequestDetail>(`/requests/${encodeURIComponent(id)}`);
  return <Async state={st}>{(r) => <Detail r={r} reload={st.reload} />}</Async>;
}
