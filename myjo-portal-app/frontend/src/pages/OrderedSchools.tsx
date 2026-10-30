/* Ordered schools (GET /ordered-schools): academic-support checklist per school, missing support first. */
import { Link } from 'react-router-dom';
import { asList } from '../api';
import { useAuth } from '../auth';
import { usePaperForm, useResourceForm, useTrainingForm } from '../forms/academicForms';
import { fd, list, nameOf, num, plural } from '../format';
import { useApi } from '../hooks';
import { requestPath } from '../nav';
import type { ListResponse, OrderedSchool } from '../types';
import { Async } from '../ui/Async';
import { Card, PageHead } from '../ui/Card';
import { Kpi } from '../ui/Kpi';
import { Pill } from '../ui/Pill';
import { SeriesTags } from '../ui/Tags';

function Check({ ok, label, detail }: { ok: boolean; label: string; detail: string }) {
  return (
    <li className={ok ? 'ok' : 'no'}>
      <span className="mk" aria-hidden="true">
        {ok ? '✓' : '✕'}
      </span>
      <span>
        <b>
          {label}
          <span className="sr-only">{ok ? ': done' : ': missing'}</span>
        </b>
        <small>{detail}</small>
      </span>
    </li>
  );
}

function SchoolCard({ s, onChanged }: { s: OrderedSchool; onChanged: () => void }) {
  const { can } = useAuth();
  const openTraining = useTrainingForm();
  const openPaper = usePaperForm();
  const openResource = useResourceForm();
  const c = s.coverage;
  const o = s.order;
  const confirmed = o.status === 'Confirmed';
  return (
    <section className={'card acs' + (c.complete ? '' : ' need')}>
      <header>
        <div style={{ minWidth: 0 }}>
          <h3>
            <Link to={requestPath(s.request_id)}>{nameOf(s.school)}</Link>
          </h3>
          <p>
            {s.city} · {nameOf(s.distributor)}
          </p>
        </div>
        <Pill s={c.complete ? 'Complete' : 'Missing'} />
      </header>
      <div className="body">
        <ul className="chk">
          <Check ok={c.training} label="Teacher training" detail={s.counts.trainings ? plural(s.counts.trainings, 'session') : 'No session yet'} />
          <Check ok={c.papers} label="Question papers" detail={s.counts.papers ? plural(s.counts.papers, 'paper') : 'None yet'} />
          <Check ok={c.resources} label="Manuals & resources" detail={s.counts.resources ? `${s.counts.resources} published for this school` : 'None published yet'} />
        </ul>
        <div className="acs-meta">
          <Pill s={confirmed ? 'Confirmed' : 'Awaiting'} />{' '}
          <span className="muted">
            {o.source === 'distributor' ? 'Placed by distributor' : 'Confirmed by Myjo'} · {fd(o.date)} · <span className="mono">{o.po}</span> · {num(o.qty)} books
          </span>
        </div>
        <div>
          <SeriesTags names={o.series} />
          <span className="sub" style={{ marginTop: 4 }}>
            Classes {list(o.classes)} · {list(o.subjects)}
          </span>
        </div>
        <div className="muted" style={{ fontSize: '.82rem' }}>
          School login: {s.login_active ? 'active' : 'not created'}
        </div>
        {can('academic') && (
          <div className="acs-act">
            <button type="button" className={'btn sm' + (c.training ? '' : ' primary')} onClick={() => void openTraining({ preselect: s.request_id, onSaved: onChanged })}>
              New training
            </button>
            <button type="button" className={'btn sm' + (c.papers ? '' : ' primary')} onClick={() => void openPaper({ preselect: s.request_id, onSaved: onChanged })}>
              New question paper
            </button>
            <button type="button" className={'btn sm' + (c.resources ? '' : ' primary')} onClick={() => void openResource({ preselect: s.request_id, onSaved: onChanged })}>
              Upload resource
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

export default function OrderedSchools() {
  const st = useApi<OrderedSchool[] | ListResponse<OrderedSchool>>('/ordered-schools');
  return (
    <>
      <PageHead title="Ordered schools" sub="Every order gets academic support: teacher training, question papers and manuals. The school’s portal opens as soon as the order is placed." />
      <Async state={st}>
        {(d) => {
          const L = asList(d);
          const missing = L.filter((s) => !s.coverage.complete).length;
          const pending = L.filter((s) => s.order.status !== 'Confirmed').length;
          return (
            <>
              <div className="kpis">
                <Kpi value={L.length} label="Schools with orders" tone="hl" />
                <Kpi value={missing} label="Orders missing academic support" tone={missing ? 'alert' : undefined} />
                <Kpi value={pending} label="Distributor orders awaiting Myjo confirmation" />
              </div>
              {L.length ? (
                <div className="acs-list">
                  {L.map((s) => (
                    <SchoolCard key={String(s.request_id)} s={s} onChanged={st.reload} />
                  ))}
                </div>
              ) : (
                <Card title="Ordered schools">
                  <p className="muted">No schools with orders yet.</p>
                </Card>
              )}
              <p className="muted" style={{ fontSize: '.82rem' }}>
                Academic support is complete when the school has a teacher-training session, at least one question paper, and published manuals it can open. Draft and archived items don’t count. Schools missing support are listed first.
              </p>
            </>
          );
        }}
      </Async>
    </>
  );
}
