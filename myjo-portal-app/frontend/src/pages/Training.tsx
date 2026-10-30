/* Teacher training list (GET /trainings?status=). */
import { useState } from 'react';
import { asList } from '../api';
import { useAuth } from '../auth';
import { useTrainingForm } from '../forms/academicForms';
import { fdt, plural } from '../format';
import { useApi } from '../hooks';
import { useMeta } from '../meta';
import { trainingPath } from '../nav';
import type { ListResponse, TrainingListItem } from '../types';
import { Async } from '../ui/Async';
import { PageHead } from '../ui/Card';
import { StatusPills } from '../ui/Pill';
import { Seg } from '../ui/Seg';
import { Table, type Column } from '../ui/Table';

export const trainingColumns: Column<TrainingListItem>[] = [
  { label: 'No.', render: (t) => <span className="mono">{t.no}</span> },
  { label: 'Session', w: true, render: (t) => <><b>{t.title}</b><span className="sub">{t.type} · AY {t.ay}</span></> },
  { label: 'Date & time', render: (t) => <span className={t.overdue ? 'late' : undefined}>{fdt(t.at)}</span> },
  { label: 'Mode', render: (t) => t.mode },
  { label: 'Trainer', render: (t) => t.trainer },
  { label: 'Schools', w: true, render: (t) => <>{plural(t.schools.length, 'school')}<span className="sub">{t.schools.map((s) => s.name).join('; ')}</span></> },
  { label: 'Expected', n: true, render: (t) => t.expected_total },
  { label: 'Attended', n: true, render: (t) => (['Completed', 'Closed'].includes(t.status) ? t.attended_total : '—') },
  { label: 'Status', render: (t) => <StatusPills status={t.status} cancelPending={t.cancel_pending} overdue={t.overdue} /> },
];

export default function Training() {
  const meta = useMeta();
  const { can } = useAuth();
  const openTraining = useTrainingForm();
  const [status, setStatus] = useState('');
  const st = useApi<TrainingListItem[] | ListResponse<TrainingListItem>>('/trainings', { status });
  return (
    <>
      <PageHead
        title="Teacher training"
        sub="Group training sessions for whole schools. One session can cover several converted schools, with attendance and feedback kept for each school."
        actions={
          can('academic') && (
            <button type="button" className="btn primary" onClick={() => void openTraining({ onSaved: st.reload })}>
              New group training
            </button>
          )
        }
      />
      <Seg label="Filter by status" options={meta.training_statuses} value={status} onChange={setStatus} />
      <Async state={st}>
        {(d) => (
          <Table
            columns={trainingColumns}
            rows={asList(d).slice().sort((a, b) => b.at.localeCompare(a.at))}
            rowKey={(t) => String(t.id)}
            rowTo={(t) => trainingPath(t.id)}
            empty="No training sessions match."
          />
        )}
      </Async>
    </>
  );
}
