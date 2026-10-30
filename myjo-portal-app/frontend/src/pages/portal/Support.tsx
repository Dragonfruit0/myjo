/* School › Support requests (GET /portal/requests, POST /portal/papers). */
import { asList } from '../../api';
import { fd } from '../../format';
import { useApi } from '../../hooks';
import type { ListResponse, PortalRequest } from '../../types';
import { Async } from '../../ui/Async';
import { Card, PageHead } from '../../ui/Card';
import { Pill } from '../../ui/Pill';
import { Table } from '../../ui/Table';
import { useSchoolPaperForm } from './useSchoolPaperForm';

export default function Support() {
  const st = useApi<ListResponse<PortalRequest>>('/portal/requests');
  const requestPaper = useSchoolPaperForm();
  return (
    <>
      <PageHead
        title="Support requests"
        sub="Raise question-paper requests and track their status. Teacher training is planned by Myjo for your whole school; see Teacher training."
        actions={<button type="button" className="btn primary" onClick={() => void requestPaper(st.reload)}>Request question paper</button>}
      />
      <Async state={st}>
        {(d) => (
          <Card title="Question papers" sub="Papers in preparation show as In Progress until Myjo publishes them" flush>
            <Table
              columns={[
                { label: 'No.', render: (p) => <span className="mono">{p.no}</span> },
                { label: 'Class · subject', render: (p) => `Class ${p.cls} · ${p.subject}` },
                { label: 'Exam', render: (p) => p.exam },
                { label: 'Required by', render: (p) => fd(p.due_date) },
                { label: 'Status', render: (p) => <Pill s={p.status} /> },
              ]}
              rows={asList(d)}
              rowKey={(p) => String(p.id)}
              empty="No question-paper requests yet."
            />
          </Card>
        )}
      </Async>
    </>
  );
}
