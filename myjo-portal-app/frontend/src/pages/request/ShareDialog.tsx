/* Share demo details: POST /requests/<id>/share records the share, notifies, and returns the message text. */
import { useState } from 'react';
import { post, toApiError } from '../../api';
import { fdt } from '../../format';
import type { RequestDetail } from '../../types';
import { useToast } from '../../ui/Toast';

export function ShareDialog({ request: r, onClose, onShared }: { request: RequestDetail; onClose: () => void; onShared: () => void }) {
  const toast = useToast();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const s = r.school;
  const mobile = (s.mobile ?? '').replace(/\D/g, '').slice(-10);

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await post<{ message: string }>(`/requests/${r.id}/share`);
      setMessage(res.message);
      toast('Shared by email and WhatsApp');
      onShared();
    } catch (e) {
      setError(toApiError(e).message);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!message) return;
    try {
      await navigator.clipboard.writeText(message);
      toast('Message copied to clipboard');
    } catch {
      toast('Your browser blocked clipboard access. Select the text and copy it.', 'bad');
    }
  };

  return (
    <>
      <p className="muted">Sends the demo details to the school contact and the distributor by email and WhatsApp.</p>
      <div className="recips">
        <div>
          <b>
            {s.contact} ({s.name})
          </b>
          <span>
            {s.email} · {s.mobile}
          </span>
        </div>
        <div>
          <b>{r.distributor?.name}</b>
          <span>{r.distributor?.phone}</span>
        </div>
      </div>
      {r.schedule?.shared_at && !message && <p className="muted">Last shared {fdt(r.schedule.shared_at)}.</p>}
      {message && (
        <pre className="msg" tabIndex={0} aria-label="Message sent">
          {message}
        </pre>
      )}
      {error && (
        <p className="ferr" role="alert">
          {error}
        </p>
      )}
      <div className="mfoot">
        {message ? (
          <>
            <button type="button" className="btn" onClick={() => void copy()}>
              Copy message
            </button>
            {mobile && (
              <a className="btn" href={`https://wa.me/91${mobile}?text=${encodeURIComponent(message)}`} target="_blank" rel="noopener noreferrer">
                Open in WhatsApp
              </a>
            )}
            <button type="button" className="btn primary" onClick={onClose}>
              Done
            </button>
          </>
        ) : (
          <>
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button type="button" className="btn primary" onClick={() => void send()} disabled={busy} aria-busy={busy}>
              {busy ? 'Sending…' : 'Send to school & distributor'}
            </button>
          </>
        )}
      </div>
    </>
  );
}
