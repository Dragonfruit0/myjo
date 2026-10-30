/* School › Download history (GET /portal/history). */
import { asList } from '../../api';
import { fdt } from '../../format';
import { useApi } from '../../hooks';
import type { DownloadLog, ListResponse } from '../../types';
import { Async } from '../../ui/Async';
import { PageHead } from '../../ui/Card';
import { Table } from '../../ui/Table';

export default function History() {
  const st = useApi<DownloadLog[] | ListResponse<DownloadLog>>('/portal/history');
  return (
    <>
      <PageHead title="Download history" sub="Everything downloaded by your school’s users." />
      <Async state={st}>
        {(d) => (
          <Table
            columns={[
              { label: 'Date & time', render: (x) => <span className="mono">{fdt(x.at)}</span> },
              { label: 'User', render: (x) => x.user },
              { label: 'Type', render: (x) => x.kind },
              { label: 'Item', w: true, render: (x) => x.item },
              { label: 'File', render: (x) => <span className="mono">{x.file}</span> },
            ]}
            rows={asList(d).slice().sort((a, b) => b.at.localeCompare(a.at))}
            rowKey={(_, i) => i}
            empty="No downloads yet."
          />
        )}
      </Async>
    </>
  );
}
