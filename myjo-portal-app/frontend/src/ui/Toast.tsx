import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';

type ToastFn = (message: string, tone?: 'bad') => void;

const ToastContext = createContext<ToastFn | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<{ text: string; tone?: 'bad' } | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const toast = useCallback<ToastFn>((text, tone) => {
    setMsg({ text, tone });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setMsg(null), tone === 'bad' ? 5000 : 3200);
  }, []);
  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div aria-live="polite" role="status">
        {msg && <div className={'toast' + (msg.tone ? ' ' + msg.tone : '')}>{msg.text}</div>}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastFn {
  const t = useContext(ToastContext);
  if (!t) throw new Error('useToast must be used inside <ToastProvider>');
  return t;
}
