/* Training session detail (GET /trainings/<id>) with schedule / completion / close / cancel actions. */
import { useParams } from 'react-router-dom';
import { asList, get, post, toApiError } from '../api';
import { useTrainingForm } from '../forms/academicForms';
import { fd, fdt, list, nowLocal, stars, timeOf, toId } from '../format';
import { useApi } from '../hooks';
import { requestPath } from '../nav';
import type { ListResponse, Resource, TrainingDetail } from '../types';
import { Async } from '../ui/Async';
import { Card, KV, Muted, Note, PageHead } from '../ui/Card';
import { fileIds, va, vs, type Field } from '../ui/Form';
import { useModal } from '../ui/Modal';
import { Pill, StatusPills } from '../ui/Pill';
import { FileChips, SeriesTags } from '../ui/Tags';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

function useCompletionForm() {
  const modal = useModal();
  const toast = useToast();
  return async (t: TrainingDetail, onSaved: () => void) => {
    let resources: Resource[] = [];
    try {
      resources = asList(await get<Resource[] | ListResponse<Resource>>('/resources'));
    } catch (e) {
      toast(toApiError(e).message, 'bad');
      return;
    }
    const c = t.completion;
    const fields: Field[] = [
      { sec: 'Session' },
      { k: 'status', label: 'Training completion status', t: 'select', o: ['Completed', 'Partially completed'], req: true },
      { k: 'recording', label: 'Recording link', t: 'url', ph: 'https://' },
      { k: 'trainer_remarks', label: 'Trainer remarks', t: 'textarea', req: true },
      { k: 'follow_up', label: 'Follow-up action, if required', t: 'textarea', rows: 2 },
      { k: 'files', label: 'Presentations, attendance sheets or other files', t: 'file', multiple: true, wide: true },
      { k: 'resource_ids', label: 'Related manuals, presentations & resources', t: 'multi', o: resources.filter((x) => x.status !== 'Cancelled' && x.status !== 'Archived').map((x) => [String(x.id), x.title + (x.status === 'Draft' ? ' (draft)' : '')] as const) },
    ];
    const initial: Record<string, unknown> = { status: 'Completed', ...(c ?? {}), resource_ids: t.resources.map((x) => String(x.id)) };
    for (const s of t.schools) {
      const id = String(s.request_id);
      const confirmNote = s.school_confirm ? ` · school ${s.school_confirm.toLowerCase()}${s.school_teachers != null ? ' ' + s.school_teachers + ' teachers' : ''}` : ' · school has not confirmed';
      fields.push(
        { sec: s.name, hint: `Expected ${s.expected}${confirmNote}` },
        { k: 'att_' + id, label: 'Actual teachers attended', t: 'number', req: true },
        { k: 'attn_' + id, label: 'Attendance', t: 'select', o: ['Attended', 'Partially attended', 'Did not attend'], req: true },
        { k: 'fb_' + id, label: 'Myjo feedback for this school', t: 'textarea', rows: 2 },
      );
      initial['att_' + id] = s.attended ?? s.school_teachers ?? '';
      initial['attn_' + id] = s.attendance ?? '';
      initial['fb_' + id] = s.myjo_feedback ?? '';
    }
    modal.form({
      title: 'Training completion · ' + t.no,
      sub: `${t.title} · ${fdt(t.at)}`,
      fields,
      initial,
      submitLabel: 'Save completion',
      validate: (v) => {
        if (t.at.slice(0, 16) > nowLocal()) return 'Completion can be recorded only after the session date & time.';
        for (const s of t.schools) {
          const id = String(s.request_id);
          const n = Number(vs(v, 'att_' + id));
          const a = vs(v, 'attn_' + id);
          if (a === 'Did not attend' && n > 0) return `${s.name}: attendance is "Did not attend" but teachers attended is ${n}.`;
          if (a !== 'Did not attend' && !(n > 0)) return `${s.name}: enter the number of teachers who attended.`;
        }
        return null;
      },
      onSubmit: async (v) => {
        await post(`/trainings/${t.id}/complete`, {
          status: vs(v, 'status'),
          trainer_remarks: vs(v, 'trainer_remarks'),
          follow_up: vs(v, 'follow_up'),
          recording: vs(v, 'recording'),
          file_ids: fileIds(v, 'files'),
          resource_ids: va(v, 'resource_ids').map(toId),
          schools: t.schools.map((s) => {
            const id = String(s.request_id);
            return { request_id: s.request_id, attended: Number(vs(v, 'att_' + id)), attendance: vs(v, 'attn_' + id), myjo_feedback: vs(v, 'fb_' + id) };
          }),
        });
        return 'Completion saved';
      },
      onSuccess: onSaved,
    });
  };
}

function Detail({ t, reload }: { t: TrainingDetail; reload: () => void }) {
  const modal = useModal();
  const toast = useToast();
  const openTraining = useTrainingForm();
  const openCompletion = useCompletionForm();
  const has = (a: TrainingDetail['actions'][number]) => t.actions.includes(a);
  const c = t.completion;
  const expected = t.schools.reduce((s, x) => s + (Number(x.expected) || 0), 0);
  const attended = t.schools.reduce((s, x) => s + (Number(x.attended) || 0), 0);
  const reported = t.schools.reduce((s, x) => s + (Number(x.school_teachers) || 0), 0);

  const schedule = async () => {
    try {
      await post(`/trainings/${t.id}/schedule`);
      toast(`Scheduled · ${t.schools.length} school${t.schools.length === 1 ? '' : 's'} notified`);
      reload();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };

  return (
    <>
      <PageHead
        back={{ to: '/training', label: 'Teacher training' }}
        eyebrow={<span className="mono">{t.no}</span>}
        title={t.title}
        sub={<>{t.type} · AY {t.ay} · <StatusPills status={t.status} cancelPending={t.cancel_pending} overdue={t.overdue} /></>}
      />
      {t.status === 'Cancelled' && t.cancel && (
        <Note title="Cancelled" meta={`Requested by ${t.cancel.by}${t.cancel.approved_by ? ' · approved by ' + t.cancel.approved_by : ''}`}>
          {t.cancel.reason}
        </Note>
      )}
      {t.actions.length > 0 && (
        <div className="actions">
          {has('edit') && <button type="button" className="btn" onClick={() => void openTraining({ existing: t, onSaved: reload })}>Edit session</button>}
          {has('schedule') && <button type="button" className="btn primary" onClick={() => void schedule()}>Schedule & notify schools</button>}
          {has('complete') && <button type="button" className={'btn' + (c ? '' : ' primary')} onClick={() => void openCompletion(t, reload)}>{c ? 'Update completion' : 'Record completion'}</button>}
          {has('close') && (
            <button type="button" className="btn primary" onClick={() => modal.reason({ title: 'Close ' + t.no, text: 'Closed sessions are kept for history and can no longer be edited.', label: 'Closing remarks (optional)', required: false, ok: 'Close session', onSubmit: async (note) => { await post(`/trainings/${t.id}/close`, note ? { note } : {}); return 'Session closed'; }, onSuccess: reload })}>
              Close session
            </button>
          )}
          {has('cancel') && (
            <button type="button" className="btn danger" onClick={() => modal.reason({ title: 'Request cancellation · ' + t.no, text: 'Records are never deleted. Admin must approve before the record is cancelled.', ok: 'Send for approval', danger: true, onSubmit: async (reason) => { await post(`/trainings/${t.id}/cancel`, { reason }); return 'Sent to Admin for approval'; }, onSuccess: reload })}>
              Cancel session
            </button>
          )}
        </div>
      )}
      <div className="grid2">
        <Card title="Session details">
          <KV
            rows={[
              ['Date & time', fdt(t.at)],
              ['Mode', t.mode],
              t.mode === 'Online' ? ['Meeting link', t.link ? <a href={t.link} target="_blank" rel="noopener noreferrer">{t.link}</a> : ''] : ['Venue', t.venue],
              ['Trainer', t.trainer],
              ['Book series', <SeriesTags names={t.series} />],
              ['Classes', list(t.classes)],
              ['Subjects', list(t.subjects)],
              ['Agenda', t.agenda],
              ['Special instructions', t.instructions],
              ['Remarks', t.remarks],
            ]}
          />
        </Card>
        <Card title="Completion">
          {c ? (
            <KV
              rows={[
                ['Completion status', <Pill s={c.status} />],
                ['Teachers attended', <><b>{attended}</b> of {expected} expected</>],
                ['Trainer remarks', c.trainer_remarks],
                ['Follow-up action', c.follow_up],
                ['Recording', c.recording ? <a href={c.recording} target="_blank" rel="noopener noreferrer">{c.recording}</a> : ''],
                ['Files', <FileChips files={c.files} staff />],
                ['Recorded by', `${c.by} · ${fdt(c.at)}`],
              ]}
            />
          ) : (
            <Muted>{t.status === 'Scheduled' ? 'Record completion after the session to capture school-wise attendance and feedback.' : 'Not completed yet.'}</Muted>
          )}
        </Card>
      </div>
      <Card title="School-wise attendance & feedback" sub={`${t.schools.length} school${t.schools.length === 1 ? '' : 's'}`} flush>
        <Table
          columns={[
            { label: 'School', render: (s) => <>{s.name}<span className="sub">{s.city}</span></> },
            { label: 'Expected', n: true, render: (s) => s.expected },
            { label: 'School confirmation', render: (s) => <Pill s={s.school_confirm || 'Awaiting'} /> },
            { label: 'Teachers (school-reported)', n: true, render: (s) => s.school_teachers ?? '—' },
            { label: 'Attended (Myjo)', n: true, render: (s) => s.attended ?? '—' },
            { label: 'Attendance', render: (s) => <Pill s={s.attendance} /> },
            { label: 'School feedback', w: true, render: (s) => (s.school_feedback ? <><span className="stars" aria-label={`${s.school_feedback.rating} out of 5`}>{stars(s.school_feedback.rating)}</span><span className="sub">{s.school_feedback.text} · {s.school_feedback.by}</span></> : '—') },
            { label: 'Myjo feedback', w: true, render: (s) => s.myjo_feedback || '—' },
          ]}
          rows={t.schools}
          rowKey={(s) => String(s.request_id)}
          rowTo={(s) => requestPath(s.request_id)}
          total={t.schools.length > 1 ? ['Total', expected, '', reported, attended, '', '', ''] : undefined}
        />
      </Card>
      <div className="grid2">
        <Card title="Related manuals & resources">
          {t.resources.length ? (
            <div className="list">
              {t.resources.map((x) => (
                <div className="li" key={String(x.id)}>
                  <span className="when">{x.no}</span>
                  <div className="t">
                    <b>{x.title}</b>
                    <span>
                      {x.type} · v{x.version}
                    </span>
                  </div>
                  <Pill s={x.status} />
                </div>
              ))}
            </div>
          ) : (
            <Muted>No resources linked.</Muted>
          )}
        </Card>
        <Card title="Training history">
          {t.history.length ? (
            <div className="list">
              {t.history.map((h, i) => (
                <div className="li" key={i}>
                  <span className="when">
                    {fd(h.at)}
                    <br />
                    {timeOf(h.at)}
                  </span>
                  <div className="t">
                    <b>{h.action}</b>
                    <span>
                      {h.school} · {h.by}
                    </span>
                  </div>
                  <span />
                </div>
              ))}
            </div>
          ) : (
            <Muted>No history yet.</Muted>
          )}
        </Card>
      </div>
    </>
  );
}

export default function TrainingDetailPage() {
  const { id = '' } = useParams();
  const st = useApi<TrainingDetail>(`/trainings/${encodeURIComponent(id)}`);
  return <Async state={st}>{(t) => <Detail t={t} reload={st.reload} />}</Async>;
}
