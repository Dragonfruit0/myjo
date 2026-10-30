/* Access control: screen and action grids per role (GET /permissions, PUT /permissions, POST /permissions/reset). */
import { useEffect, useState } from 'react';
import { post, put, toApiError } from '../api';
import { useAuth } from '../auth';
import { useApi } from '../hooks';
import type { PermissionGrid, Role } from '../types';
import { Async } from '../ui/Async';
import { Card, PageHead } from '../ui/Card';
import { useModal } from '../ui/Modal';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

type Kind = 'screen' | 'action';
type Row = { code: string; label: string; eligible: Record<string, boolean> };

export default function Access() {
  const st = useApi<PermissionGrid>('/permissions');
  const { refresh } = useAuth();
  const toast = useToast();
  const modal = useModal();
  const [granted, setGranted] = useState<PermissionGrid['granted'] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (st.data) setGranted(st.data.granted);
  }, [st.data]);

  const isOn = (kind: Kind, role: string, code: string) => (granted?.[kind === 'screen' ? 'screens' : 'actions'][role] ?? []).includes(code);

  const change = async (kind: Kind, role: Role, roleLabel: string, row: Row, on: boolean) => {
    const id = `${kind}|${role}|${row.code}`;
    setBusy(id);
    try {
      // PUT returns the whole grid; use it as the new state.
      const next = await put<PermissionGrid>('/permissions', { role, kind, code: row.code, granted: on });
      setGranted(next.granted);
      toast(`${roleLabel}: ${row.label} ${on ? 'granted' : 'removed'}`);
      void refresh();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    } finally {
      setBusy(null);
    }
  };

  const restore = () =>
    modal.form({
      title: 'Restore default access',
      sub: 'Every role goes back to the standard screens and permissions.',
      fields: [{ k: '_x', label: 'This affects', t: 'static', html: 'All roles except Admin' }],
      submitLabel: 'Restore defaults',
      danger: true,
      onSubmit: async () => {
        await post('/permissions/reset');
        void refresh();
        return 'Default access restored';
      },
      onSuccess: st.reload,
    });

  const grid = (kind: Kind, rows: Row[], roles: PermissionGrid['roles'], first: string) => (
    <Table
      columns={[
        { label: first, render: (r: Row) => r.label },
        ...roles.map(({ code: role, label: roleLabel }) => ({
          label: roleLabel,
          render: (r: Row) => {
            if (role === 'admin') return <span className="pill good" title="Admin always has full access">Always</span>;
            if (!r.eligible[role]) return <span className="muted" title="Not available for this role" aria-label="Not available">—</span>;
            const id = `${kind}|${role}|${r.code}`;
            return (
              <span className="acc-cell">
                <input type="checkbox" checked={isOn(kind, role, r.code)} disabled={busy === id} onChange={(e) => void change(kind, role, roleLabel, r, e.target.checked)} aria-label={`${roleLabel}: ${r.label}`} />
              </span>
            );
          },
        })),
      ]}
      rows={rows}
      rowKey={(r) => r.code}
    />
  );

  return (
    <>
      <PageHead
        title="Access control"
        sub="Choose which screens each role can open and which actions it can take. Changes apply immediately and are recorded in the audit trail. Admin always keeps full access, including users, subjects & series and this page."
        actions={<button type="button" className="btn danger" onClick={restore}>Restore defaults</button>}
      />
      <Async state={st}>
        {(d) => (
          <>
            <Card title="Screen access by role" sub="Distributors are limited to their own schools; school users only ever see their own school’s published items" flush>
              {grid('screen', d.screens, d.roles, 'Screen')}
            </Card>
            <Card title="Action permissions by role" sub="A role also needs the matching screen to reach an action" flush>
              {grid('action', d.actions, d.roles, 'Action')}
            </Card>
            <Card title="Admin-only areas">
              <p className="muted">Users & roles, Subjects & series, and Access control are always restricted to Admin.</p>
            </Card>
          </>
        )}
      </Async>
    </>
  );
}
