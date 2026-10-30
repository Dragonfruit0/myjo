/* Audit trail (GET /audit?q=&entity=&limit=300). */
import { useState } from 'react';
import { useApi, useDebounced } from '../hooks';
import type { AuditEntry } from '../types';
import { Async } from '../ui/Async';
import { PageHead } from '../ui/Card';
import { Table } from '../ui/Table';

export default function Audit() {
  const [q, setQ] = useState('');
  const [entity, setEntity] = useState('');
  const dq = useDebounced(q);
  const st = useApi<{ items: AuditEntry[]; entities: string[] }>('/audit', { q: dq, entity, limit: 300 });
  // The entity list comes from the server so the filter keeps all options while filtered.
  const entities = st.data?.entities ?? [];
  return (
    <>
      <PageHead title="Audit trail" sub="Every action with user, date, time, old value and new value. Entries cannot be edited or deleted." />
      <div className="filters">
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search reference, user, action, value…" aria-label="Search audit" />
        <select value={entity} onChange={(e) => setEntity(e.target.value)} aria-label="Record type">
          <option value="">All records</option>
          {entities.map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </div>
      <Async state={st}>
        {(d) => {
          const rows = d.items;
          return (
            <div className="stack" style={{ gap: 8 }}>
              <p className="muted">
                {rows.length} entr{rows.length === 1 ? 'y' : 'ies'}
                {rows.length === 300 ? ' (latest 300)' : ''}
              </p>
              <Table
                columns={[
                  { label: 'Date & time', render: (a) => <span className="mono">{a.at.replace('T', ' ')}</span> },
                  { label: 'User', render: (a) => a.user },
                  { label: 'Record', render: (a) => a.entity },
                  { label: 'Reference', render: (a) => <span className="mono">{a.ref}</span> },
                  { label: 'Action', render: (a) => a.action },
                  { label: 'Field', render: (a) => a.field },
                  { label: 'Old value', w: true, render: (a) => a.old },
                  { label: 'New value', w: true, render: (a) => a.new },
                ]}
                rows={rows}
                rowKey={(_, i) => i}
                empty="No audit entries match."
              />
            </div>
          );
        }}
      </Async>
    </>
  );
}
