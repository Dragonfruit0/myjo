/* Cards on the request detail page (same content and order as the prototype). */
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { fd, fdt, list, num, pad, today } from '../../format';
import { trainingPath } from '../../nav';
import type { AuditEntry, RequestDetail } from '../../types';
import { Card, KV, Muted, Note } from '../../ui/Card';
import { Pill } from '../../ui/Pill';
import { FileChips, SeriesTags, useStaffDownloads } from '../../ui/Tags';
import { Table } from '../../ui/Table';
import { ActionButtons, type ActionButton } from './useRequestActions';

type R = { r: RequestDetail };

export function Steps({ r }: R) {
  return (
    <div className="steps" role="list" aria-label="Workflow progress">
      {r.steps.map((s, i) => (
        <div role="listitem" key={s.label} className={'step' + (s.done ? ' done' : '') + (s.stopped ? ' stop' : '')}>
          <i aria-hidden="true" />
          <b>{pad(i + 1)}</b>
          {s.label}
          <span className="sr-only">{s.stopped ? ' (stopped)' : s.done ? ' (done)' : ' (not yet)'}</span>
        </div>
      ))}
    </div>
  );
}

export function SchoolCard({ r }: R) {
  const s = r.school;
  return (
    <Card title="School & request">
      <KV
        rows={[
          ['School', s.name],
          ['Address', [s.address, s.city, s.state].filter(Boolean).join(', ') + (s.pincode ? ' – ' + s.pincode : '')],
          ['Board / AY', `${s.board} · ${r.ay}`],
          ['Contact', [s.contact, s.designation].filter(Boolean).join(' · ')],
          ['Mobile / email', <><span className="mono">{s.mobile}</span> · {s.email}</>],
          ['Classes', list(r.classes)],
          ['Subjects', list(r.subjects)],
          ['Series of interest', <SeriesTags names={r.series} />],
          ['Student strength', s.strength != null ? num(s.strength) : ''],
          ['Expected order qty', r.exp_qty != null ? num(r.exp_qty) : ''],
          ['Preferred demo', r.pref_date ? `${fd(r.pref_date)} · ${r.pref_time ?? ''}` : ''],
          ['Distributor', <>{r.distributor?.name} · <span className="mono">{r.distributor?.phone}</span></>],
          ['Remarks', r.remarks],
          ['Assigned to', r.assigned_to],
        ]}
      />
    </Card>
  );
}

export function NotesCard({ r }: R) {
  if (!r.notes.length) return null;
  return (
    <Card title="Review notes">
      {r.notes.slice().reverse().map((n, i) => (
        <Note key={i} title={n.type} meta={`${n.by} · ${fdt(n.at)}`}>
          {n.text}
        </Note>
      ))}
    </Card>
  );
}

export function DistOrderCard({ r, buttons }: R & { buttons: ActionButton[] }) {
  const staff = useStaffDownloads();
  const q = r.dist_order;
  if (!q) return null;
  if (q.direct) {
    return (
      <Card title="Order created by distributor" sub="Order details are in the Book order card">
        <KV
          rows={[
            ['Status', <><Pill s="Confirmed" /> <span className="muted">by {q.by} · {fdt(q.at)}</span></>],
            ['PO / ref', <span className="mono">{q.po}</span>],
            ['Quantity', <><b>{num(q.qty)}</b> books</>],
            ['PO copy', <FileChips files={q.files} staff={staff} />],
            ['Note', 'Final order created by the distributor; no Myjo approval needed'],
          ]}
        />
      </Card>
    );
  }
  return (
    <Card title="Order placed by distributor" sub={q.status === 'Submitted' ? 'Waiting for Myjo Marketing to confirm' : undefined} actions={buttons.length ? <ActionButtons buttons={buttons} /> : undefined}>
      <KV
        rows={[
          ['Status', <Pill s={q.status} />],
          ['Placed by', `${q.by} · ${fdt(q.at)}`],
          ['Academic year', q.ay],
          ['Distributor PO / ref', <span className="mono">{q.po}</span>],
          ['Book series', <SeriesTags names={q.series} />],
          ['Classes · subjects', `${list(q.classes)} · ${list(q.subjects)}`],
          ['Quantity', <><b>{num(q.qty)}</b> books</>],
          ['Required delivery', fd(q.req_delivery)],
          ['Remarks', q.remarks],
          ['PO copy', <FileChips files={q.files} staff={staff} />],
          q.review_note ? ['Myjo note', <>{q.review_note}{q.reviewed_by && <span className="sub">{q.reviewed_by} · {fdt(q.reviewed_at)}</span>}</>] : null,
        ]}
      />
    </Card>
  );
}

export function PackCard({ r }: R) {
  const a = r.academic;
  const k = a?.pack;
  if (!a || !k) return null;
  const t = a.trainings.find((x) => String(x.id) === String(k.training_id));
  const papers = a.papers.filter((p) => k.paper_ids.map(String).includes(String(p.id)));
  const published = papers.filter((p) => ['Published', 'Delivered'].includes(p.status)).length;
  return (
    <Card title="Academic support set up with the order" sub={a.coverage.complete ? 'Academic support complete' : 'Academic support: ' + a.coverage.missing.join(', ') + ' still needed'}>
      <KV
        rows={[
          ['Teacher training', t ? <><Link to={trainingPath(t.id)}>{t.no}</Link> · {fdt(t.at)} <Pill s={t.status} /></> : '—'],
          ['Question papers', <>{papers.length} requested · {published} published <span className="sub">{[...new Set(papers.map((p) => p.exam))].join(', ')}</span></>],
          ['Manuals & resources', `${k.resource_ids.length} shared for ${list(r.order?.series)}`],
          ['Set up by', `${k.by} · ${fdt(k.at)}`],
        ]}
      />
    </Card>
  );
}

export function OrderCard({ r, confirmed }: R & { confirmed: boolean }) {
  const o = r.order;
  return (
    <Card title="Book order">
      <KV
        rows={[
          ['Order status', <Pill s={r.order_status} />],
          ['Converted', r.status === 'Converted' ? <span className="pill good">Yes · school has purchased</span> : <span className="pill neutral">Not yet</span>],
        ]}
      />
      {o && confirmed && (
        <KV
          rows={[
            ['Academic year', o.ay],
            ['Book series', <SeriesTags names={o.series} />],
            ['Classes / subjects', `${list(o.classes)} · ${list(o.subjects)}`],
            ['Quantity ordered', num(o.qty)],
            ['PO / reference', <span className="mono">{o.po}</span>],
            ['Confirmed on', fd(o.conf_date)],
            ['Expected delivery', fd(o.del_date)],
            ['Payment', <Pill s={o.payment} />],
            ['Source', o.source === 'distributor' ? 'Distributor order' : 'Myjo'],
            ['Remarks', o.remarks],
          ]}
        />
      )}
    </Card>
  );
}

export function ScheduleCard({ r, buttons }: R & { buttons: ActionButton[] }) {
  const s = r.schedule;
  if (!s) return null;
  return (
    <Card title="Demo schedule" actions={buttons.length ? <ActionButtons buttons={buttons} /> : undefined}>
      <KV
        rows={[
          ['Date & time', fdt(s.at)],
          ['Mode', s.mode + (s.platform ? ' · ' + s.platform : '')],
          s.mode === 'Online'
            ? ['Meeting link', s.link ? <a href={s.link} target="_blank" rel="noopener noreferrer">{s.link}</a> : '']
            : ['Venue', s.venue],
          ['Presenter', s.presenter],
          ['Marketing person', s.marketing],
          ['Agenda', s.agenda],
          ['Instructions', s.instructions],
          ['Shared with school', s.shared_at ? fdt(s.shared_at) : <Pill s="Not shared yet" />],
          ['Reminder', s.reminded ? 'Sent' : 'Sends automatically 48 hours before'],
        ]}
      />
    </Card>
  );
}

export function FeedbackCard({ r, buttons }: R & { buttons: ActionButton[] }) {
  const staff = useStaffDownloads();
  const fb = r.feedback;
  if (!fb) return null;
  return (
    <Card title="Myjo demo feedback" sub="Internal · not visible to distributors or schools" actions={buttons.length ? <ActionButtons buttons={buttons} size="sm" /> : undefined}>
      <KV
        rows={[
          ['Conducted by', `${fb.by} · ${fd(fb.date)}`],
          ['Attendees', fb.attendees],
          ['Designations', fb.designations],
          ['Classes / subjects', `${list(fb.classes)} · ${list(fb.subjects)}`],
          ['Series demonstrated', <SeriesTags names={fb.series} />],
          ['Interest level', <Pill s={fb.interest} />],
          ['Requirements', fb.requirements],
          ['Requested', list(fb.requested)],
          ['Concerns raised', fb.objections],
          ['Competitor in use', fb.competitor],
          ['Next follow-up', fd(fb.next_follow)],
          ['Internal remarks', fb.remarks],
          ['Documents', <FileChips files={fb.files} staff={staff} />],
        ]}
      />
    </Card>
  );
}

export function MarketingCard({ r }: R) {
  const m = r.marketing;
  const fus = (r.followups ?? []).slice().sort((a, b) => b.at.localeCompare(a.at));
  if (!m && !fus.length) return null;
  const overdue = !!m?.next_follow && m.next_follow < today() && !['Converted', 'Not Converted'].includes(r.status);
  return (
    <Card title="Marketing & follow-up">
      {m ? (
        <KV
          rows={[
            ['School potential', <Pill s={m.potential} />],
            ['Decision maker', [m.dm_name, m.dm_desig].filter(Boolean).join(' · ')],
            ['DM contact', <><span className="mono">{m.dm_mobile}</span> · {m.dm_email}</>],
            ['Competitor', m.competitor],
            ['Expected order qty', m.exp_qty != null ? num(m.exp_qty) : ''],
            ['Expected decision', fd(m.decision_date)],
            ['Discussion stage', m.stage],
            ['Next action', m.next_action],
            ['Next follow-up', m.next_follow ? <span className={overdue ? 'late' : undefined}>{fd(m.next_follow)}</span> : ''],
            ['Assigned', m.person],
            ['Remarks', m.remarks],
          ]}
        />
      ) : (
        <Muted>No marketing feedback yet.</Muted>
      )}
      <div>
        <div className="eyebrow" style={{ margin: '6px 0' }}>
          Follow-up history · {fus.length}
        </div>
        {fus.length ? (
          <div className="list">
            {fus.map((f) => (
              <div className="li" key={String(f.id)}>
                <span className="when">
                  {fd(f.at)}
                  <br />
                  {f.at.slice(11, 16)}
                </span>
                <div className="t">
                  <b>
                    {f.method} · {f.person}
                  </b>
                  <span>{f.summary}</span>
                  <span>
                    Next: {f.next_action || '—'}
                    {f.next_date ? ' by ' + fd(f.next_date) : ''} · by {f.by}
                  </span>
                </div>
                <span />
              </div>
            ))}
          </div>
        ) : (
          <Muted>No follow-ups logged.</Muted>
        )}
      </div>
    </Card>
  );
}

export function AcademicCard({ r, actions }: R & { actions?: ReactNode }) {
  const a = r.academic;
  if (!a || !a.eligible) return null;
  return (
    <Card title="Academic support" actions={actions}>
      <KV
        rows={[
          ['Coverage', a.coverage.complete ? <Pill s="Complete" /> : <><Pill s="Missing" /> <span className="muted">{a.coverage.missing.join(', ')}</span></>],
          [
            'Group trainings',
            a.trainings.length ? (
              <>
                {a.trainings.map((t) => (
                  <div key={String(t.id)}>
                    <Link to={trainingPath(t.id)}>{t.no}</Link> {t.title} <Pill s={t.status} />
                  </div>
                ))}
              </>
            ) : (
              'None yet'
            ),
          ],
          [
            'Question papers',
            a.papers.length ? (
              <div className="tags">
                {a.papers.map((p) => (
                  <span key={String(p.id)}>
                    {p.no} <Pill s={p.status} />
                  </span>
                ))}
              </div>
            ) : (
              'None yet'
            ),
          ],
          ['Manuals & resources', String(a.resources_count)],
          ['School login', a.login ? <>{a.login.username} · {a.login.active ? 'active' : <Pill s="Inactive" />}</> : '—'],
        ]}
      />
    </Card>
  );
}

export function AuditCard({ entries }: { entries: AuditEntry[] }) {
  return (
    <Card title="Audit trail for this request" flush>
      <Table
        columns={[
          { label: 'When', render: (x) => <span className="mono">{fdt(x.at)}</span> },
          { label: 'User', render: (x) => x.user },
          { label: 'Action', render: (x) => x.action },
          { label: 'Field', render: (x) => x.field },
          { label: 'Old value', w: true, render: (x) => x.old },
          { label: 'New value', w: true, render: (x) => x.new },
        ]}
        rows={entries.slice(0, 40)}
        rowKey={(_, i) => i}
      />
    </Card>
  );
}
