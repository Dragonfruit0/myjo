/* School › Overview (GET /portal/overview). */
import { Link } from 'react-router-dom';
import { useUser } from '../../auth';
import { fd, list, timeOf } from '../../format';
import { useApi } from '../../hooks';
import type { PortalOverview } from '../../types';
import { Async } from '../../ui/Async';
import { Card, KV, Muted } from '../../ui/Card';
import { Kpi } from '../../ui/Kpi';
import { Pill } from '../../ui/Pill';
import { SeriesTags } from '../../ui/Tags';
import { useSchoolPaperForm } from './useSchoolPaperForm';

export default function PortalOverviewPage() {
  const user = useUser();
  const st = useApi<PortalOverview>('/portal/overview');
  const requestPaper = useSchoolPaperForm();

  return (
    <Async state={st}>
      {(d) => {
        const s = d.school;
        const o = d.order;
        const confirmed = o.status === 'Confirmed';
        return (
          <>
            <div className="portal-hero">
              <div>
                <div className="eyebrow">Academic Support & Resource Library</div>
                <h1>{s.name || user.school_name}</h1>
                <p className="muted">
                  {[s.city, s.state].filter(Boolean).join(', ')}
                  {s.board ? ' · ' + s.board : ''} · Signed in as {user.name}
                </p>
              </div>
              <div className="actions">
                <Link className="btn primary" to="/portal/training">
                  Teacher training
                </Link>
                <button type="button" className="btn" onClick={() => void requestPaper(st.reload, d)}>
                  Request question paper
                </button>
              </div>
            </div>
            <div className="kpis">
              <Kpi value={d.kpis.papers} label="Question papers available" link="library" tone="hl" />
              <Kpi value={d.kpis.resources} label="Manuals & resources" link="library" />
              <Kpi value={d.kpis.upcoming} label="Upcoming training sessions" link="mytraining" />
              <Kpi value={d.kpis.my_downloads} label="My downloads" link="history" />
            </div>
            <div className="grid2">
              <Card title="Your Myjo books">
                <KV
                  rows={[
                    ['Order status', confirmed ? <Pill s="Confirmed" /> : <><Pill s="Awaiting" /> <span className="muted">Placed by your distributor; Myjo will confirm</span></>],
                    ['Book series', <SeriesTags names={o.series} />],
                    ['Classes', list(o.classes)],
                    ['Subjects', list(o.subjects)],
                    ['Academic year', o.ay],
                    ['Order reference', <span className="mono">{o.po}</span>],
                    ['Expected delivery', fd(o.delivery)],
                  ]}
                />
              </Card>
              <Card title="Upcoming teacher training">
                {d.upcoming_trainings.length ? (
                  <div className="list">
                    {d.upcoming_trainings.map((t) => {
                      return (
                        <Link className="li go" key={String(t.id)} to="/portal/training">
                          <span className="when">
                            {fd(t.at)}
                            <br />
                            {timeOf(t.at)}
                          </span>
                          <div className="t">
                            <b>{t.title}</b>
                            <span>
                              {t.mode} · Trainer {t.trainer}
                              {` · ${t.expected} teachers expected`}
                            </span>
                          </div>
                          <Pill s={t.confirm || 'Awaiting'} />
                        </Link>
                      );
                    })}
                  </div>
                ) : (
                  <Muted>No upcoming sessions. Myjo schedules group training for your school and notifies you by email and WhatsApp.</Muted>
                )}
              </Card>
            </div>
            <Card title="Recent updates for your school">
              {d.updates.length ? (
                <div className="list">
                  {d.updates.map((n, i) => (
                    <div className="li" key={i}>
                      <span className="when">{fd(n.at)}</span>
                      <div className="t">
                        <b>{n.event}</b>
                        <span>{n.message}</span>
                      </div>
                      <span className="muted" style={{ fontSize: '.76rem' }}>
                        Email + WhatsApp
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <Muted>No updates yet.</Muted>
              )}
            </Card>
          </>
        );
      }}
    </Async>
  );
}
