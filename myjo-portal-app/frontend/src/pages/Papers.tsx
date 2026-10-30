/* Question papers (GET /papers?status=) with per-row actions from each paper's `actions`. */
import { useState } from 'react';
import { asList, post, toApiError } from '../api';
import { useAuth } from '../auth';
import { usePaperForm } from '../forms/academicForms';
import { fd } from '../format';
import { useApi } from '../hooks';
import { useMeta } from '../meta';
import type { ListResponse, Paper } from '../types';
import { Async } from '../ui/Async';
import { PageHead } from '../ui/Card';
import { useModal } from '../ui/Modal';
import { Pill, StatusPills } from '../ui/Pill';
import { Seg } from '../ui/Seg';
import { FileChips } from '../ui/Tags';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

const LIVE = ['Published', 'Delivered'];

export function paperContext(p: { id: Paper['id'] }, kind: 'qp' | 'ak') {
  return `paper:${p.id}:${kind}`;
}

function access(p: Paper) {
  if (p.status === 'Cancelled') return <Pill s="Hidden" />;
  if (LIVE.includes(p.status)) return <Pill s={p.revoked ? 'Revoked' : 'Downloadable'} />;
  return <span className="muted">Not visible</span>;
}

export default function Papers() {
  const meta = useMeta();
  const { can } = useAuth();
  const modal = useModal();
  const toast = useToast();
  const openPaper = usePaperForm();
  const [status, setStatus] = useState('');
  const st = useApi<Paper[] | ListResponse<Paper>>('/papers', { status });

  const act = (p: Paper, path: string, msg: string) => async () => {
    try {
      await post(`/papers/${p.id}/${path}`);
      toast(msg);
      st.reload();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };

  const rowActions = (p: Paper) => {
    const has = (a: Paper['actions'][number]) => (p.actions ?? []).includes(a);
    return (
      <div className="row-actions">
        {has('edit') && <button type="button" className="btn sm" onClick={() => void openPaper({ existing: p, onSaved: st.reload })}>Edit</button>}
        {has('publish') && <button type="button" className="btn sm primary" onClick={act(p, 'publish', `${p.no} published · school notified`)}>Publish</button>}
        {has('deliver') && <button type="button" className="btn sm" onClick={act(p, 'deliver', 'Marked delivered')}>Mark delivered</button>}
        {has('revoke') && (
          <button type="button" className="btn sm danger" onClick={() => modal.reason({ title: 'Revoke school access · ' + p.no, text: `${p.school} will no longer see or download this paper.`, ok: 'Revoke access', danger: true, onSubmit: async (reason) => { await post(`/papers/${p.id}/revoke`, { reason }); return 'Access revoked'; }, onSuccess: st.reload })}>
            Revoke access
          </button>
        )}
        {has('restore') && <button type="button" className="btn sm" onClick={act(p, 'restore', 'Access restored')}>Restore access</button>}
        {has('cancel') && (
          <button type="button" className="btn sm ghost" onClick={() => modal.reason({ title: 'Request cancellation · ' + p.no, text: 'Records are never deleted. Admin must approve before the record is cancelled.', ok: 'Send for approval', danger: true, onSubmit: async (reason) => { await post(`/papers/${p.id}/cancel`, { reason }); return 'Sent to Admin for approval'; }, onSuccess: st.reload })}>
            Cancel
          </button>
        )}
      </div>
    );
  };

  return (
    <>
      <PageHead
        title="Question papers"
        sub="Prepared by the Myjo Academic Team for converted schools. Schools see a paper only after it is published."
        actions={can('academic') && <button type="button" className="btn primary" onClick={() => void openPaper({ onSaved: st.reload })}>New question paper</button>}
      />
      <Seg label="Filter by status" options={meta.paper_statuses} value={status} onChange={setStatus} />
      <Async state={st}>
        {(d) => (
          <Table
            columns={[
              { label: 'No.', render: (p) => <><span className="mono">{p.no}</span><span className="sub">by {p.raised_by}</span></> },
              { label: 'School', render: (p) => p.school },
              { label: 'Class · subject', render: (p) => <>Class {p.cls} · {p.subject}<span className="sub">{p.series}</span></> },
              { label: 'Exam', render: (p) => <>{p.exam}<span className="sub">AY {p.ay}</span></> },
              { label: 'Due', render: (p) => <span className={p.overdue ? 'late' : undefined}>{fd(p.due_date)}</span> },
              { label: 'Assigned', render: (p) => p.assignee || '—' },
              { label: 'Files', w: true, render: (p) => <FileChips files={[p.qp_file, p.ak_file]} context={(f) => paperContext(p, p.ak_file && f.id === p.ak_file.id ? 'ak' : 'qp')} /> },
              { label: 'Marks', n: true, render: (p) => p.max_marks ?? '—' },
              { label: 'Status', render: (p) => <StatusPills status={p.status} cancelPending={p.cancel_pending} /> },
              { label: 'School access', render: access },
              { label: 'Actions', render: rowActions },
            ]}
            rows={asList(d).slice().sort((a, b) => a.due_date.localeCompare(b.due_date))}
            rowKey={(p) => String(p.id)}
            empty="No question papers match."
          />
        )}
      </Async>
    </>
  );
}
