/* Downloads (GET /downloads?request_id=): totals by school and the download log. */
import { useState } from 'react';
import { fdt } from '../format';
import { useApi } from '../hooks';
import type { Downloads } from '../types';
import { Async } from '../ui/Async';
import { PageHead } from '../ui/Card';
import { Pill } from '../ui/Pill';
import { Table } from '../ui/Table';

export default function DownloadsPage() {
  const [school, setSchool] = useState('');
  const all = useApi<Downloads>('/downloads');
  const filtered = useApi<Downloads>(school ? '/downloads' : null, { request_id: school });
  const logState = school ? filtered : all;

  return (
    <>
      <PageHead title="Downloads" sub="Every download is recorded with school, user, resource, date and time." />
      <Async state={all}>
        {(d) => (
          <>
            <Table
              columns={[
                { label: 'School', render: (x) => x.school },
                { label: 'Question papers & keys', n: true, render: (x) => x.papers },
                { label: 'Manuals & resources', n: true, render: (x) => x.resources },
                { label: 'Total', n: true, render: (x) => x.papers + x.resources },
                { label: 'Last download', render: (x) => (x.last ? fdt(x.last) : <Pill s="No downloads" />) },
              ]}
              rows={d.by_school}
              rowKey={(x) => String(x.request_id)}
              empty="No ordered schools yet."
            />
            <div className="filters">
              <select value={school} onChange={(e) => setSchool(e.target.value)} aria-label="School">
                <option value="">All schools</option>
                {d.by_school.map((x) => (
                  <option key={String(x.request_id)} value={String(x.request_id)}>
                    {x.school}
                  </option>
                ))}
              </select>
            </div>
          </>
        )}
      </Async>
      <Async state={logState}>
        {(d) => (
          <Table
            columns={[
              { label: 'Date & time', render: (x) => <span className="mono">{fdt(x.at)}</span> },
              { label: 'School', render: (x) => x.school },
              { label: 'User', render: (x) => x.user },
              { label: 'Type', render: (x) => x.kind },
              { label: 'Resource', w: true, render: (x) => x.item },
              { label: 'File', render: (x) => <span className="mono">{x.file}</span> },
            ]}
            rows={d.log}
            rowKey={(_, i) => i}
            empty="No downloads yet."
            caption="Download log"
          />
        )}
      </Async>
    </>
  );
}
