/* First sign-in with a temporary login: choose a password and PIN (POST /auth/setup). */
import { useState, type FormEvent } from 'react';
import { toApiError } from '../api';
import { useAuth } from '../auth';
import { pinProblem, pwProblem } from './passwordRules';

export default function Setup() {
  const { user, setup, logout } = useAuth();
  const [pw1, setPw1] = useState('');
  const [pw2, setPw2] = useState('');
  const [pin1, setPin1] = useState('');
  const [pin2, setPin2] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const digits = (s: string) => s.replace(/\D/g, '').slice(0, 4);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = pwProblem(pw1) ?? (pw1 !== pw2 ? 'The two passwords do not match.' : null) ?? pinProblem(pin1) ?? (pin1 !== pin2 ? 'The two PINs do not match.' : null);
    if (problem) return setError(problem);
    setBusy(true);
    setError(null);
    try {
      await setup(pw1, pin1);
    } catch (err) {
      setError(toApiError(err).message);
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <div className="login-head">
        <h1>Set your password and PIN</h1>
        <p className="muted">Welcome, {user?.name}. You signed in with a temporary login. Choose your own password and PIN to continue.</p>
      </div>
      <form className="card login-form" onSubmit={submit} noValidate>
        <div className="body">
          <div className="field">
            <span className="lab">Username</span>
            <div className="static mono">{user?.username}</div>
          </div>
          <div className="field">
            <label htmlFor="np1">New password</label>
            <input type="password" id="np1" autoComplete="new-password" value={pw1} onChange={(e) => setPw1(e.target.value)} aria-describedby="np1h" autoFocus />
            <small id="np1h">At least 8 characters, with letters and numbers</small>
          </div>
          <div className="field">
            <label htmlFor="np2">Confirm new password</label>
            <input type="password" id="np2" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="pn1">New 4-digit PIN</label>
            <input type="password" id="pn1" inputMode="numeric" maxLength={4} autoComplete="off" className="pin" value={pin1} onChange={(e) => setPin1(digits(e.target.value))} aria-describedby="pn1h" />
            <small id="pn1h">Used for quick sign-in on this portal</small>
          </div>
          <div className="field">
            <label htmlFor="pn2">Confirm PIN</label>
            <input type="password" id="pn2" inputMode="numeric" maxLength={4} autoComplete="off" className="pin" value={pin2} onChange={(e) => setPin2(digits(e.target.value))} />
          </div>
          {error && (
            <p className="ferr" role="alert">
              {error}
            </p>
          )}
          <div className="mfoot">
            <button type="button" className="btn" onClick={() => void logout()}>
              Cancel
            </button>
            <button type="submit" className="btn primary" disabled={busy} aria-busy={busy}>
              {busy ? 'Saving…' : 'Save and continue'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
