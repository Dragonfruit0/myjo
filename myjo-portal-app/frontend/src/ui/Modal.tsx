/*
 * One modal at a time (opening another replaces it, as in the prototype).
 *   const modal = useModal();
 *   modal.form({ title, fields, initial, onSubmit: async (v) => { await post(...); return 'Saved'; }, onSuccess: reload });
 *   modal.reason({ title, text, ok: 'Reject request', onSubmit: async (reason) => ... });
 *   modal.open({ title, render: (close) => <p>…</p> });
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Form, vs, type Field, type FormValues } from './Form';
import { useToast } from './Toast';

interface ModalSpec {
  title: string;
  sub?: ReactNode;
  render: (close: () => void) => ReactNode;
}

export interface FormSpec {
  title: string;
  sub?: ReactNode;
  fields: Field[];
  initial?: Record<string, unknown>;
  submitLabel?: string;
  danger?: boolean;
  validate?: (v: FormValues) => string | null | undefined;
  onSubmit: (v: FormValues) => Promise<string | void>;
  onSuccess?: () => void;
  fieldAliases?: Record<string, string>;
}

export interface ReasonSpec {
  title: string;
  text?: ReactNode;
  label?: string;
  required?: boolean;
  ok?: string;
  danger?: boolean;
  onSubmit: (reason: string) => Promise<string | void>;
  onSuccess?: () => void;
}

interface ModalApi {
  open: (spec: ModalSpec) => void;
  close: () => void;
  form: (spec: FormSpec) => void;
  reason: (spec: ReasonSpec) => void;
}

const ModalContext = createContext<ModalApi | null>(null);

function Dialog({ spec, onClose }: { spec: ModalSpec; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = 'mtitle';

  useEffect(() => {
    const el = ref.current?.querySelector<HTMLElement>('.mb input:not([type=hidden]):not([type=checkbox]):not([type=file]), .mb select, .mb textarea, .mb button, .x');
    el?.focus();
  }, [spec]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab' && ref.current) {
        const f = ref.current.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),input:not([disabled]),select,textarea,[tabindex]:not([tabindex="-1"])');
        if (!f.length) return;
        const first = f[0];
        const last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby={titleId} ref={ref}>
        <header>
          <div>
            <h3 id={titleId}>{spec.title}</h3>
            {spec.sub && <p>{spec.sub}</p>}
          </div>
          <button type="button" className="x" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <div className="mb">{spec.render(onClose)}</div>
      </div>
    </div>
  );
}

export function ModalProvider({ children }: { children: ReactNode }) {
  const [spec, setSpec] = useState<ModalSpec | null>(null);
  const [version, setVersion] = useState(0);
  const returnFocus = useRef<HTMLElement | null>(null);
  const isOpen = useRef(false);
  const toast = useToast();

  const open = useCallback((s: ModalSpec) => {
    // Keep the element that opened the first dialog of a chain (e.g. Create order → Next → order form).
    if (!returnFocus.current) returnFocus.current = document.activeElement as HTMLElement | null;
    isOpen.current = true;
    setSpec(s);
    setVersion((n) => n + 1);
  }, []);

  const close = useCallback(() => {
    isOpen.current = false;
    setSpec(null);
    window.setTimeout(() => {
      if (isOpen.current) return; // another dialog opened straight away
      const el = returnFocus.current;
      returnFocus.current = null;
      if (el && document.contains(el)) el.focus();
    }, 0);
  }, []);

  const form = useCallback(
    (f: FormSpec) =>
      open({
        title: f.title,
        sub: f.sub,
        render: (closeIt) => (
          <Form
            fields={f.fields}
            initial={f.initial}
            submitLabel={f.submitLabel}
            danger={f.danger}
            validate={f.validate}
            fieldAliases={f.fieldAliases}
            onSubmit={f.onSubmit}
            onCancel={closeIt}
            onDone={(msg) => {
              closeIt();
              if (msg) toast(msg);
              f.onSuccess?.();
            }}
          />
        ),
      }),
    [open, toast],
  );

  const reason = useCallback(
    (r: ReasonSpec) =>
      form({
        title: r.title,
        sub: r.text,
        fields: [{ k: 'reason', label: r.label ?? 'Reason', t: 'textarea', req: r.required !== false }],
        submitLabel: r.ok ?? 'Confirm',
        danger: r.danger,
        onSubmit: (v) => r.onSubmit(vs(v, 'reason')),
        onSuccess: r.onSuccess,
      }),
    [form],
  );

  const value = useMemo(() => ({ open, close, form, reason }), [open, close, form, reason]);

  return (
    <ModalContext.Provider value={value}>
      {children}
      {spec && <Dialog key={version} spec={spec} onClose={close} />}
    </ModalContext.Provider>
  );
}

export function useModal(): ModalApi {
  const m = useContext(ModalContext);
  if (!m) throw new Error('useModal must be used inside <ModalProvider>');
  return m;
}
