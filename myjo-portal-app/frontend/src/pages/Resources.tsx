/* Manuals & resources (GET /resources?status=) with publish / archive / access / cancel. */
import { useState } from 'react';
import { asList, post, put, toApiError } from '../api';
import { useAuth } from '../auth';
import { ACCESS_ALL, useResourceForm } from '../forms/academicForms';
import { fd, toId } from '../format';
import { useApi } from '../hooks';
import { useMeta } from '../meta';
import type { ListResponse, Resource, ResourceAction } from '../types';
import { Async } from '../ui/Async';
import { PageHead } from '../ui/Card';
import { va } from '../ui/Form';
import { useModal } from '../ui/Modal';
import { StatusPills } from '../ui/Pill';
import { Seg } from '../ui/Seg';
import { FileChips, SeriesTag } from '../ui/Tags';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

export const resourceContext = (x: { id: Resource['id'] }) => `resource:${x.id}`;

export default function Resources() {
  const meta = useMeta();
  const { can } = useAuth();
  const modal = useModal();
  const toast = useToast();
  const openResource = useResourceForm();
  const [status, setStatus] = useState('');
  const st = useApi<Resource[] | ListResponse<Resource>>('/resources', { status });

  const act = (x: Resource, path: string, msg: string) => async () => {
    try {
      await post(`/resources/${x.id}/${path}`);
      toast(msg);
      st.reload();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };

  const manageAccess = (x: Resource) => {
    modal.form({
      title: 'Manage school access · ' + x.title,
      sub: 'Ticked schools are blocked from seeing and downloading this resource.',
      fields: [{ k: 'revoked_ids', label: 'Revoke access for', t: 'multi', o: x.audience.map((a) => [String(a.id), a.name] as const) }],
      initial: { revoked_ids: x.revoked_ids.map(String) },
      submitLabel: 'Save access',
      onSubmit: async (v) => {
        await put(`/resources/${x.id}/access`, { revoked_ids: va(v, 'revoked_ids').map(toId) });
        return 'Access updated';
      },
      onSuccess: st.reload,
    });
  };

  const rowActions = (x: Resource) => {
    const has = (a: ResourceAction) => x.actions.includes(a);
    return (
      <div className="row-actions">
        {has('edit') && <button type="button" className="btn sm" onClick={() => void openResource({ existing: x, onSaved: st.reload })}>Edit</button>}
        {has('publish') && <button type="button" className="btn sm primary" onClick={act(x, 'publish', 'Published · schools notified')}>Publish</button>}
        {has('archive') && <button type="button" className="btn sm" onClick={act(x, 'archive', 'Archived · hidden from schools')}>Archive</button>}
        {has('access') && <button type="button" className="btn sm" onClick={() => manageAccess(x)}>Manage access</button>}
        {has('cancel') && (
          <button type="button" className="btn sm ghost" onClick={() => modal.reason({ title: 'Request cancellation · ' + x.no, text: 'Records are never deleted. Admin must approve before the record is cancelled.', ok: 'Send for approval', danger: true, onSubmit: async (reason) => { await post(`/resources/${x.id}/cancel`, { reason }); return 'Sent to Admin for approval'; }, onSuccess: st.reload })}>
            Cancel
          </button>
        )}
      </div>
    );
  };

  return (
    <>
      <PageHead
        title="Teacher training manuals & resources"
        sub="Manuals, guides, lesson plans, slides, videos, worksheets and assessment guidelines. Drafts and archived items are never shown to schools."
        actions={can('academic') && <button type="button" className="btn primary" onClick={() => void openResource({ onSaved: st.reload })}>Upload resource</button>}
      />
      <Seg label="Filter by status" options={meta.resource_statuses} value={status} onChange={setStatus} />
      <Async state={st}>
        {(d) => (
          <Table
            columns={[
              {
                label: 'Resource', w: true,
                render: (x) => (
                  <>
                    <b>{x.title}</b>
                    <span className="sub mono">{x.no}</span>
                    {x.link ? <a className="sub" href={x.link} target="_blank" rel="noopener noreferrer">{x.link}</a> : <FileChips files={[x.file]} context={() => resourceContext(x)} />}
                  </>
                ),
              },
              { label: 'Type', render: (x) => x.type },
              { label: 'Series', render: (x) => <SeriesTag name={x.series} /> },
              { label: 'Class · subject', render: (x) => `${x.cls} · ${x.subject}` },
              { label: 'AY', render: (x) => x.ay },
              { label: 'Ver.', render: (x) => x.version },
              { label: 'Uploaded', render: (x) => <>{fd(x.upload_date)}<span className="sub">{x.uploaded_by}</span></> },
              { label: 'Access', w: true, render: (x) => <>{x.access === ACCESS_ALL ? 'All ordered schools' : x.schools.join('; ')}{x.revoked.length > 0 && <span className="sub late">Revoked: {x.revoked.join('; ')}</span>}</> },
              { label: 'Status', render: (x) => <StatusPills status={x.status} cancelPending={x.cancel_pending} /> },
              { label: 'Downloads', n: true, render: (x) => x.downloads },
              { label: 'Actions', render: rowActions },
            ]}
            rows={asList(d)}
            rowKey={(x) => String(x.id)}
            empty="No resources match."
          />
        )}
      </Async>
    </>
  );
}
