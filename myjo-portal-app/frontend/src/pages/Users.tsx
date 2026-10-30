/* Users & roles (GET/POST/PUT /users, POST /users/<id>/toggle|reset). Users are deactivated, never deleted. */
import { Link } from 'react-router-dom';
import { asList, post, put, toApiError } from '../api';
import { useUser } from '../auth';
import { loadOrderedSchools } from '../forms/academicForms';
import { nameOf, toId } from '../format';
import { useApi } from '../hooks';
import { ROLE_LABEL, ROLES } from '../nav';
import type { ListResponse, ManagedUser, OrderedSchool } from '../types';
import { Async } from '../ui/Async';
import { PageHead } from '../ui/Card';
import { vs, type Field, type FormValues } from '../ui/Form';
import { useModal } from '../ui/Modal';
import { Pill } from '../ui/Pill';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

const isDist = (v: FormValues) => vs(v, 'role') === 'dist';
const isSchool = (v: FormValues) => vs(v, 'role') === 'school';

function userFields(schools: OrderedSchool[], isNew: boolean): Field[] {
  return [
    { k: 'name', label: 'Full name', req: true },
    { k: 'username', label: 'Username', req: true, hint: 'Letters, numbers, dots, dashes' },
    { k: 'email', label: 'Email', t: 'email', req: true },
    { k: 'phone', label: 'Mobile number', t: 'tel', req: true },
    { k: 'role', label: 'Role', t: 'select', o: ROLES.map((r) => [r, ROLE_LABEL[r]] as const), req: true },
    { k: 'org', label: 'Distributor company', when: isDist },
    { k: 'school_request_id', label: 'School', t: 'select', o: schools.map((s) => [String(s.request_id), `${nameOf(s.school)} · ${s.city}`] as const), hint: 'Only ordered schools can have portal logins', when: isSchool },
    ...(isNew
      ? ([
          { sec: 'Temporary login', hint: 'The user must choose their own password and PIN at first sign-in' },
          { k: 'temp_password', label: 'Temporary password', req: true, autoComplete: 'off' },
          { k: 'temp_pin', label: 'Temporary 4-digit PIN', req: true, pin: true },
        ] as Field[])
      : []),
  ];
}

function userCheck(v: FormValues, isNew: boolean): string | null {
  if (!/^[a-z0-9._-]{3,40}$/i.test(vs(v, 'username'))) return 'Username must be 3–40 letters, numbers, dots or dashes.';
  if (isNew && vs(v, 'temp_password').length < 8) return 'Temporary password must be at least 8 characters.';
  if (isNew && !/^\d{4}$/.test(vs(v, 'temp_pin'))) return 'PIN must be exactly 4 digits.';
  if (isDist(v) && !vs(v, 'org')) return 'Enter the distributor company.';
  if (isSchool(v) && !vs(v, 'school_request_id')) return 'Choose the school for this login.';
  return null;
}

function userBody(v: FormValues) {
  return {
    name: vs(v, 'name'),
    username: vs(v, 'username').toLowerCase(),
    email: vs(v, 'email').toLowerCase(),
    phone: vs(v, 'phone'),
    role: vs(v, 'role'),
    ...(isDist(v) ? { org: vs(v, 'org') } : {}),
    ...(isSchool(v) ? { school_request_id: toId(vs(v, 'school_request_id')) } : {}),
  };
}

export default function Users() {
  const me = useUser();
  const modal = useModal();
  const toast = useToast();
  const st = useApi<ManagedUser[] | ListResponse<ManagedUser>>('/users');

  const openUser = async (u: ManagedUser | null) => {
    let schools: OrderedSchool[] = [];
    try {
      schools = await loadOrderedSchools();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
      return;
    }
    modal.form({
      title: u ? 'Edit ' + u.name : 'Add user',
      fields: userFields(schools, !u),
      initial: u ? { ...u, school_request_id: u.school_id != null ? String(u.school_id) : '' } : { role: 'demo' },
      submitLabel: u ? 'Save changes' : 'Add user',
      validate: (v) => userCheck(v, !u),
      onSubmit: async (v) => {
        if (u) {
          await put(`/users/${u.id}`, userBody(v));
          return 'User updated';
        }
        await post('/users', { ...userBody(v), temp_password: vs(v, 'temp_password'), temp_pin: vs(v, 'temp_pin') });
        return `User added · share the temporary password and PIN with ${vs(v, 'name')}`;
      },
      onSuccess: st.reload,
    });
  };

  const reset = (u: ManagedUser) =>
    modal.form({
      title: 'Reset login · ' + u.name,
      sub: 'Sets a temporary password and PIN and unlocks the account. The user must choose their own at the next sign-in.',
      fields: [
        { k: '_u', label: 'Username', t: 'static', html: <span className="mono">{u.username}</span> },
        { k: 'temp_password', label: 'Temporary password', req: true, hint: 'At least 8 characters', autoComplete: 'off' },
        { k: 'temp_pin', label: 'Temporary 4-digit PIN', req: true, pin: true },
      ],
      submitLabel: 'Reset login',
      validate: (v) => (vs(v, 'temp_password').length < 8 ? 'Temporary password must be at least 8 characters.' : !/^\d{4}$/.test(vs(v, 'temp_pin')) ? 'PIN must be exactly 4 digits.' : null),
      onSubmit: async (v) => {
        await post(`/users/${u.id}/reset`, { temp_password: vs(v, 'temp_password'), temp_pin: vs(v, 'temp_pin') });
        return 'Login reset · share the temporary password and PIN with ' + u.name;
      },
      onSuccess: st.reload,
    });

  const toggle = (u: ManagedUser) =>
    modal.reason({
      title: (u.active ? 'Deactivate ' : 'Reactivate ') + u.name,
      text: u.active ? 'They will no longer be able to sign in.' : undefined,
      ok: u.active ? 'Deactivate' : 'Reactivate',
      danger: u.active,
      onSubmit: async (reason) => {
        await post(`/users/${u.id}/toggle`, { reason });
        return 'User updated';
      },
      onSuccess: st.reload,
    });

  return (
    <>
      <PageHead
        title="Users & roles"
        sub="Users are deactivated, never deleted. School logins are also created automatically when an order is confirmed. Set what each role can do under Access control."
        actions={
          <>
            <button type="button" className="btn primary" onClick={() => void openUser(null)}>
              Add user
            </button>
            <Link className="btn" to="/access">
              Access control
            </Link>
          </>
        }
      />
      <Async state={st}>
        {(d) => (
          <Table
            columns={[
              { label: 'Name', render: (u) => u.name },
              { label: 'Username', render: (u) => <span className="mono">{u.username}</span> },
              { label: 'Role', render: (u) => u.role_label || ROLE_LABEL[u.role] },
              { label: 'Organisation / school', render: (u) => u.org || u.school_name || 'Myjo Publications' },
              { label: 'Email', render: (u) => u.email },
              { label: 'Mobile', render: (u) => <span className="mono">{u.phone}</span> },
              { label: 'Status', render: (u) => <><Pill s={u.active ? 'Active' : 'Inactive'} />{u.locked && <> <Pill s="Locked" /></>}{u.temporary && <> <Pill s="Temporary login" /></>}</> },
              {
                label: 'Actions',
                render: (u) => (
                  <div className="row-actions">
                    <button type="button" className="btn sm" onClick={() => void openUser(u)}>Edit</button>
                    <button type="button" className="btn sm" onClick={() => reset(u)}>{u.locked ? 'Unlock / reset' : 'Reset login'}</button>
                    {String(u.id) === String(me.id) ? <span className="muted">You</span> : <button type="button" className="btn sm" onClick={() => toggle(u)}>{u.active ? 'Deactivate' : 'Reactivate'}</button>}
                  </div>
                ),
              },
            ]}
            rows={asList(d)}
            rowKey={(u) => String(u.id)}
            empty="No users yet."
          />
        )}
      </Async>
    </>
  );
}
