/*
 * Sign-in: choose a designation, then username + password, or username + PIN.
 * Accounts are never listed and no sample credentials are shown.
 * Adding a designation code to the link (e.g. #distributor) preselects that tile.
 */
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { toApiError } from '../api';
import { useAuth } from '../auth';
import { ROLE_DESC, ROLE_DOT, ROLE_LABEL, ROLE_SLUG, ROLES } from '../nav';
import type { Role } from '../types';

function roleFromHash(): Role | null {
  const h = window.location.hash.slice(1);
  return ROLES.find((r) => ROLE_SLUG[r] === h) ?? null;
}

export default function Login() {
  const { login, notice, lastRole } = useAuth();
  const [role, setRole] = useState<Role | null>(() => roleFromHash() ?? lastRole);
  const [mode, setMode] = useState<'pw' | 'pin'>('pw');
  const [username, setUsername] = useState('');
  const [secret, setSecret] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const userRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onHash = () => {
      const r = roleFromHash();
      if (r) setRole(r);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    if (role) userRef.current?.focus();
  }, [role, mode]);

  const pick = (r: Role) => {
    setRole(r);
    setError(null);
    setSecret('');
  };

  const switchMode = (m: 'pw' | 'pin') => {
    setMode(m);
    setSecret('');
    setError(null);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!role || busy) return;
    const u = username.trim();
    if (mode === 'pw' && (!u || !secret)) return setError('Enter your username and password.');
    if (mode === 'pin') {
      if (!u) return setError('Enter your username.');
      if (!/^\d{4}$/.test(secret)) return setError('Enter your 4-digit PIN.');
    }
    setBusy(true);
    setError(null);
    try {
      await login(role, u, mode === 'pw' ? { password: secret } : { pin: secret });
    } catch (err) {
      setError(toApiError(err).message);
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <div className="login-head">
        <h1>Sign in to the Myjo portal</h1>
        <p className="muted">Choose your designation, then sign in with your username and password or your PIN.</p>
      </div>
      {notice && (
        <p className="note" role="status">
          {notice}
        </p>
      )}
      <div className="roles" role="group" aria-label="Designation">
        {ROLES.map((r) => (
          <button key={r} type="button" className={'role-tile' + (role === r ? ' on' : '')} aria-pressed={role === r} onClick={() => pick(r)}>
            <i style={{ background: ROLE_DOT[r] }} aria-hidden="true" />
            <b>{ROLE_LABEL[r]}</b>
            <span>{ROLE_DESC[r]}</span>
          </button>
        ))}
      </div>

      {role && (
        <form className="card login-form" onSubmit={submit} noValidate>
          <header>
            <div>
              <h3>{ROLE_LABEL[role]} sign-in</h3>
            </div>
            <div className="seg" role="group" aria-label="Sign-in method">
              <button type="button" className={mode === 'pw' ? 'on' : undefined} aria-pressed={mode === 'pw'} onClick={() => switchMode('pw')}>
                Password
              </button>
              <button type="button" className={mode === 'pin' ? 'on' : undefined} aria-pressed={mode === 'pin'} onClick={() => switchMode('pin')}>
                PIN
              </button>
            </div>
          </header>
          <div className="body">
            <div className="field">
              <label htmlFor="lgname">{mode === 'pw' ? 'Username or email' : 'Username'}</label>
              <input id="lgname" ref={userRef} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoCapitalize="off" spellCheck={false} />
            </div>
            {mode === 'pw' ? (
              <div className="field">
                <label htmlFor="lgpw">Password</label>
                <div className="pwrow">
                  <input id="lgpw" type={show ? 'text' : 'password'} value={secret} onChange={(e) => setSecret(e.target.value)} autoComplete="current-password" />
                  <button type="button" className="btn sm" aria-pressed={show} onClick={() => setShow((s) => !s)}>
                    {show ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="field">
                <label htmlFor="lgpin">4-digit PIN</label>
                <input id="lgpin" type="password" className="pin" inputMode="numeric" maxLength={4} autoComplete="off" value={secret} onChange={(e) => setSecret(e.target.value.replace(/\D/g, '').slice(0, 4))} />
              </div>
            )}
            {error && (
              <p className="ferr" role="alert">
                {error}
              </p>
            )}
            <div className="mfoot">
              <button type="submit" className="btn primary" disabled={busy} aria-busy={busy}>
                {busy ? 'Signing in…' : 'Sign in'}
              </button>
            </div>
          </div>
        </form>
      )}
      <p className="muted" style={{ fontSize: '.8rem' }}>
        Direct links: add a designation code (for example <span className="mono">#distributor</span>) to the end of this page’s link so that designation’s sign-in opens straight away. Forgot your password or PIN? Ask Admin to reset your login.
      </p>
    </div>
  );
}
