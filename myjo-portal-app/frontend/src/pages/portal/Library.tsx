/* School › Library & downloads (GET /portal/library?cls=&subject=&series=&ay=&type=&exam=&q=). */
import { useState } from 'react';
import { fd } from '../../format';
import { useApi, useDebounced } from '../../hooks';
import { useMeta } from '../../meta';
import type { PortalLibrary } from '../../types';
import { Async } from '../../ui/Async';
import { Card, PageHead } from '../../ui/Card';
import { DownloadButton, SeriesTag } from '../../ui/Tags';
import { Table } from '../../ui/Table';
import { paperContext } from '../Papers';
import { ResourceButton } from './ResourceButton';

type Key = 'cls' | 'subject' | 'series' | 'ay' | 'type' | 'exam';

export default function Library() {
  const meta = useMeta();
  const [f, setF] = useState<Partial<Record<Key, string>>>({});
  const [q, setQ] = useState('');
  const dq = useDebounced(q);
  const st = useApi<PortalLibrary>('/portal/library', { ...f, q: dq });

  const sel = (k: Key, label: string, opts: string[]) => (
    <select value={f[k] ?? ''} onChange={(e) => setF((x) => ({ ...x, [k]: e.target.value }))} aria-label={label}>
      <option value="">{label}: all</option>
      {opts.map((o) => (
        <option key={o}>{o}</option>
      ))}
    </select>
  );

  return (
    <>
      <PageHead title="Library & downloads" sub="Only items published for your school appear here. Every download is recorded." />
      <div className="filters">
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title, subject, series…" aria-label="Search library" />
        {sel('cls', 'Class', meta.classes)}
        {sel('subject', 'Subject', meta.subjects)}
        {sel('series', 'Series', st.data?.series?.length ? st.data.series : meta.series.map((s) => s.name))}
        {sel('ay', 'Year', meta.academic_years)}
        {sel('type', 'Resource type', meta.resource_types)}
        {sel('exam', 'Exam type', meta.exam_types)}
      </div>
      <Async state={st}>
        {(d) => (
          <>
            <Card title="Question papers & answer keys" sub={`${d.papers.length} available`} flush>
              <Table
                columns={[
                  { label: 'Paper', render: (p) => <>Class {p.cls} · {p.subject}<span className="sub mono">{p.no}</span></> },
                  { label: 'Series', render: (p) => <SeriesTag name={p.series} /> },
                  { label: 'Exam', render: (p) => p.exam },
                  { label: 'AY', render: (p) => p.ay },
                  { label: 'Marks', n: true, render: (p) => p.max_marks ?? '—' },
                  { label: 'Published', render: (p) => fd(p.published_at) },
                  {
                    label: 'Download',
                    render: (p) => (
                      <div className="row-actions">
                        {p.qp_file && <DownloadButton file={p.qp_file} context={paperContext(p, 'qp')}>Question paper</DownloadButton>}
                        {p.ak_file && <DownloadButton file={p.ak_file} context={paperContext(p, 'ak')} className="btn sm">Answer key</DownloadButton>}
                      </div>
                    ),
                  },
                ]}
                rows={d.papers}
                rowKey={(p) => String(p.id)}
                empty="No published question papers match."
              />
            </Card>
            <Card title="Teacher training manuals & resources" sub={`${d.resources.length} available`} flush>
              <Table
                columns={[
                  { label: 'Resource', w: true, render: (x) => <><b>{x.title}</b><span className="sub">{x.description}</span></> },
                  { label: 'Type', render: (x) => x.type },
                  { label: 'Series', render: (x) => <SeriesTag name={x.series} /> },
                  { label: 'Class · subject', render: (x) => `${x.cls} · ${x.subject}` },
                  { label: 'AY', render: (x) => x.ay },
                  { label: 'Version', render: (x) => x.version },
                  { label: 'Download', render: (x) => <ResourceButton resource={x} /> },
                ]}
                rows={d.resources}
                rowKey={(x) => String(x.id)}
                empty="No resources match."
              />
            </Card>
          </>
        )}
      </Async>
    </>
  );
}
