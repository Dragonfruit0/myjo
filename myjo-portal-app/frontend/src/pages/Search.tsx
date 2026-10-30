/* Global search (GET /search?q=). */
import { useSearchParams } from 'react-router-dom';
import { nameOf } from '../format';
import { useApi } from '../hooks';
import { trainingPath } from '../nav';
import type { SearchResults } from '../types';
import { Async } from '../ui/Async';
import { Card, PageHead } from '../ui/Card';
import { Pill } from '../ui/Pill';
import { SeriesTag } from '../ui/Tags';
import { Table } from '../ui/Table';
import { RequestTable } from './Requests';

export default function Search() {
  const [params] = useSearchParams();
  const q = (params.get('q') ?? '').trim();
  const st = useApi<SearchResults>(q ? '/search' : null, { q });
  if (!q) return <PageHead title="Search" sub="Type in the search box above to find schools, requests, sessions, papers and resources." />;
  return (
    <Async state={st}>
      {(d) => {
        const R = d.requests ?? [];
        const T = d.trainings ?? [];
        const P = d.papers ?? [];
        const M = d.resources ?? [];
        return (
          <>
            <PageHead title="Search results" sub={`“${q}” · ${R.length + T.length + P.length + M.length} matches`} />
            <Card title="Schools & demo requests" sub={`${R.length} found`} flush>
              <RequestTable rows={R} empty="No schools or requests match." />
            </Card>
            {M.length > 0 && (
              <Card title="Resources" sub={`${M.length} found`} flush>
                <Table
                  columns={[
                    { label: 'Resource', render: (x) => x.title },
                    { label: 'Type', render: (x) => x.type },
                    { label: 'Series', render: (x) => <SeriesTag name={x.series} /> },
                    { label: 'Status', render: (x) => <Pill s={x.status} /> },
                  ]}
                  rows={M}
                  rowKey={(x) => String(x.id)}
                  rowTo={() => '/resources'}
                />
              </Card>
            )}
            {P.length > 0 && (
              <Card title="Question papers" sub={`${P.length} found`} flush>
                <Table
                  columns={[
                    { label: 'No.', render: (p) => <span className="mono">{p.no}</span> },
                    { label: 'School', render: (p) => nameOf(p.school) },
                    { label: 'Class · subject', render: (p) => `Class ${p.cls} ${p.subject}` },
                    { label: 'Status', render: (p) => <Pill s={p.status} /> },
                  ]}
                  rows={P}
                  rowKey={(p) => String(p.id)}
                  rowTo={() => '/papers'}
                />
              </Card>
            )}
            {T.length > 0 && (
              <Card title="Group training sessions" sub={`${T.length} found`} flush>
                <Table
                  columns={[
                    { label: 'No.', render: (t) => <span className="mono">{t.no}</span> },
                    { label: 'Session', render: (t) => t.title },
                    { label: 'Schools', w: true, render: (t) => t.schools },
                    { label: 'Status', render: (t) => <Pill s={t.status} /> },
                  ]}
                  rows={T}
                  rowKey={(t) => String(t.id)}
                  rowTo={(t) => trainingPath(t.id)}
                />
              </Card>
            )}
          </>
        );
      }}
    </Async>
  );
}
