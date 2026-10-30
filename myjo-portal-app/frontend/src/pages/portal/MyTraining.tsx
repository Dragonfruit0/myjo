/* School › Teacher training (GET /portal/trainings) with attendance confirmation and feedback. */
import { asList, post } from '../../api';
import { fd, fdt, list, stars } from '../../format';
import { useApi } from '../../hooks';
import type { ListResponse, PortalTraining } from '../../types';
import { Async } from '../../ui/Async';
import { Card, KV, PageHead } from '../../ui/Card';
import { vs } from '../../ui/Form';
import { useModal } from '../../ui/Modal';
import { Pill } from '../../ui/Pill';
import { SeriesTags } from '../../ui/Tags';
import { ResourceButton } from './ResourceButton';

function Session({ t, reload }: { t: PortalTraining; reload: () => void }) {
  const modal = useModal();
  const s = t.mine;
  const scheduled = t.status === 'Scheduled';

  const confirm = () =>
    modal.form({
      title: 'Confirm attendance',
      sub: `${t.title} · ${fdt(t.at)}`,
      fields: [
        { k: 'confirm', label: 'Will your school attend?', t: 'select', o: ['Confirmed', 'Declined'], req: true },
        { k: 'teachers', label: 'Number of teachers attending', t: 'number', hint: `Myjo expects ${s.expected} teachers`, when: (v) => vs(v, 'confirm') !== 'Declined' },
        { k: 'note', label: 'Note for Myjo', t: 'textarea', rows: 2 },
      ],
      initial: { confirm: s.confirm || 'Confirmed', teachers: s.teachers ?? s.expected },
      submitLabel: 'Send confirmation',
      validate: (v) => (vs(v, 'confirm') === 'Confirmed' && !(Number(vs(v, 'teachers')) > 0) ? 'Enter how many teachers will attend.' : null),
      onSubmit: async (v) => {
        const declined = vs(v, 'confirm') === 'Declined';
        await post(`/portal/trainings/${t.id}/confirm`, { confirm: vs(v, 'confirm'), teachers: declined ? 0 : Number(vs(v, 'teachers')), note: vs(v, 'note') });
        return 'Confirmation sent to Myjo';
      },
      onSuccess: reload,
    });

  const feedback = () =>
    modal.form({
      title: 'Training feedback',
      sub: `${t.title} · ${fd(t.at)}`,
      fields: [
        { k: 'rating', label: 'Overall rating', t: 'select', o: [['5', '5 · Excellent'], ['4', '4 · Good'], ['3', '3 · Average'], ['2', '2 · Below average'], ['1', '1 · Poor']], req: true },
        { k: 'attended', label: 'Number of teachers who attended', t: 'number', req: true },
        { k: 'text', label: 'Feedback from your school', t: 'textarea', req: true },
      ],
      initial: { rating: s.feedback?.rating ?? '', attended: s.attended ?? s.teachers ?? '', text: s.feedback?.text ?? '' },
      submitLabel: 'Submit feedback',
      onSubmit: async (v) => {
        await post(`/portal/trainings/${t.id}/feedback`, { rating: Number(vs(v, 'rating')), attended: Number(vs(v, 'attended')), text: vs(v, 'text') });
        return 'Thank you, feedback sent';
      },
      onSuccess: reload,
    });

  const action = t.can_confirm ? (
    <button type="button" className={'btn' + (s.confirm ? '' : ' primary')} onClick={confirm}>
      {s.confirm ? 'Update attendance confirmation' : 'Confirm attendance'}
    </button>
  ) : t.can_feedback ? (
    <button type="button" className={'btn' + (s.feedback ? '' : ' primary')} onClick={feedback}>
      {s.feedback ? 'Edit feedback' : 'Submit feedback'}
    </button>
  ) : undefined;

  const resources = t.resources;
  return (
    <Card title={t.title} sub={`${t.no} · ${t.type}`} actions={action}>
      <KV
        rows={[
          ['Status', <Pill s={t.status} />],
          ['Date & time', <b>{fdt(t.at)}</b>],
          ['Mode', t.mode],
          t.mode === 'Online'
            ? ['Meeting link', scheduled ? (t.link ? <a href={t.link} target="_blank" rel="noopener noreferrer">{t.link}</a> : 'Myjo will share the link') : <span className="muted">Session over</span>]
            : ['Venue', t.venue],
          ['Trainer', <>{t.trainer}{t.trainer_contact && <span className="sub">{t.trainer_contact}</span>}</>],
          ['Series · classes · subjects', <><SeriesTags names={t.series} /><span className="sub">Classes {list(t.classes)} · {list(t.subjects)}</span></>],
          ['Agenda', t.agenda],
          ['Instructions', t.instructions],
          ['Expected from your school', `${s.expected} teachers`],
          ['Your confirmation', s.confirm ? `${s.confirm}${s.teachers != null ? ' · ' + s.teachers + ' teachers' : ''}` : <Pill s="Not confirmed yet" />],
          ['Attendance recorded by Myjo', s.attendance ? `${s.attendance} · ${s.attended ?? 0} teachers` : ''],
          ['Your feedback', s.feedback ? <><span className="stars" aria-label={`${s.feedback.rating} out of 5`}>{stars(s.feedback.rating)}</span> · {s.feedback.text}</> : ''],
          [
            'Manuals & resources',
            resources.length ? (
              <div className="list">
                {resources.map((x) => (
                  <div className="li" key={String(x.id)}>
                    <span className="when">{x.type.split(' ')[0]}</span>
                    <div className="t">
                      <b>{x.title}</b>
                      <span>v{x.version}</span>
                    </div>
                    <ResourceButton resource={x} />
                  </div>
                ))}
              </div>
            ) : (
              <span className="muted">None shared yet</span>
            ),
          ],
        ]}
      />
    </Card>
  );
}

export default function PortalTrainingPage() {
  const st = useApi<ListResponse<PortalTraining>>('/portal/trainings');
  return (
    <>
      <PageHead title="Teacher training" sub="Group training sessions Myjo has scheduled for your school. Confirm attendance before the session and share feedback afterwards." />
      <Async state={st}>
        {(d) => {
          const all = asList(d);
          const up = all.filter((t) => t.status === 'Scheduled').sort((a, b) => a.at.localeCompare(b.at));
          const past = all.filter((t) => t.status !== 'Scheduled').sort((a, b) => b.at.localeCompare(a.at));
          return (
            <>
              {up.length ? (
                up.map((t) => <Session key={String(t.id)} t={t} reload={st.reload} />)
              ) : (
                <Card title="Upcoming sessions">
                  <p className="muted">No upcoming training sessions. Myjo will notify you by email and WhatsApp when one is scheduled.</p>
                </Card>
              )}
              {past.length > 0 && (
                <>
                  <h2 className="h2-gap">Training history</h2>
                  {past.map((t) => (
                    <Session key={String(t.id)} t={t} reload={st.reload} />
                  ))}
                </>
              )}
            </>
          );
        }}
      </Async>
    </>
  );
}
