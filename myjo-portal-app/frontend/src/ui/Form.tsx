/*
 * Form builder driven by a field-spec array (same idea as the prototype's openForm).
 *
 *   const fields: Field[] = [
 *     { sec: 'School' },
 *     { k: 'school.name', label: 'School name', req: true, wide: true },
 *     { k: 'classes', label: 'Classes', t: 'multi', o: meta.classes, req: true },
 *     { k: 'venue', label: 'Venue', t: 'textarea', when: (v) => vs(v, 'mode') === 'Offline' },
 *   ];
 *
 * Keys normally equal the API field names so a server error `{"field": "pincode"}` lands on the
 * right input. Values are strings, string[] (multi) or FileRef[] (file, already uploaded through
 * POST /files). Client checks give quick feedback; the server's answer is always shown.
 */
import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { toApiError, uploadFile } from '../api';
import type { FileRef } from '../types';

export type Opt = string | readonly [string, string];
export type FieldType =
  | 'text' | 'email' | 'tel' | 'number' | 'date' | 'time' | 'datetime-local' | 'url' | 'password' | 'color'
  | 'select' | 'multi' | 'textarea' | 'file' | 'static';

export type FormValue = string | string[] | FileRef[];
export type FormValues = Record<string, FormValue>;

export interface InputField {
  k: string;
  label: string;
  t?: FieldType;
  req?: boolean;
  wide?: boolean;
  hint?: string;
  ph?: string;
  /** options for select / multi: plain strings or [value, label] */
  o?: readonly Opt[];
  rows?: number;
  multiple?: boolean;
  accept?: string;
  /** 6-digit Indian pincode */
  pincode?: boolean;
  /** 4-digit PIN entry */
  pin?: boolean;
  /** content of a `static` field */
  html?: ReactNode;
  autoComplete?: string;
  when?: (v: FormValues) => boolean;
}

export interface SectionField {
  sec: string;
  hint?: string;
  when?: (v: FormValues) => boolean;
}

export type Field = InputField | SectionField;

export const isSection = (f: Field): f is SectionField => 'sec' in f;

/* ---------- value helpers ---------- */

export const vs = (v: FormValues, k: string): string => {
  const x = v[k];
  return typeof x === 'string' ? x.trim() : '';
};
export const va = (v: FormValues, k: string): string[] => {
  const x = v[k];
  return Array.isArray(x) ? x.filter((i): i is string => typeof i === 'string') : [];
};
export const vf = (v: FormValues, k: string): FileRef[] => {
  const x = v[k];
  return Array.isArray(x) ? x.filter((i): i is FileRef => typeof i === 'object' && i !== null) : [];
};
export const fileIds = (v: FormValues, k: string) => vf(v, k).map((f) => f.id);
export const firstFileId = (v: FormValues, k: string) => vf(v, k)[0]?.id ?? null;

const isFileRef = (x: unknown): x is FileRef => !!x && typeof x === 'object' && 'name' in x && 'id' in x;

function normalize(f: InputField, raw: unknown): FormValue {
  if (f.t === 'multi') return Array.isArray(raw) ? raw.map(String) : [];
  if (f.t === 'file') {
    if (Array.isArray(raw)) return raw.filter(isFileRef);
    return isFileRef(raw) ? [raw] : [];
  }
  if (raw === null || raw === undefined) return '';
  if (typeof raw === 'number' || typeof raw === 'boolean') return String(raw);
  if (typeof raw !== 'string') return '';
  if (f.t === 'datetime-local') return raw.slice(0, 16);
  if (f.t === 'date') return raw.slice(0, 10);
  if (f.t === 'time') return raw.slice(0, 5);
  return raw;
}

const optVal = (o: Opt) => (typeof o === 'string' ? o : o[0]);
const optLabel = (o: Opt) => (typeof o === 'string' ? o : o[1]);

/* ---------- validation (same messages as the prototype) ---------- */

export function checkField(f: InputField, x: FormValue): string | null {
  const blank = x === '' || (Array.isArray(x) && x.length === 0);
  if (f.req && blank) return `${f.label} is required.`;
  if (blank || typeof x !== 'string') return null;
  const s = x.trim();
  if (f.t === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)) return `${f.label} must be a valid email address.`;
  if (f.t === 'tel' && !/^(\+?91)?[6-9]\d{9}$/.test(s.replace(/[\s-]/g, ''))) return `${f.label} must be a 10-digit Indian mobile number.`;
  if (f.pincode && !/^\d{6}$/.test(s)) return `${f.label} must be 6 digits.`;
  if (f.pin && !/^\d{4}$/.test(s)) return `${f.label} must be exactly 4 digits.`;
  if (f.t === 'url' && !/^https?:\/\/\S+$/.test(s)) return `${f.label} must start with https://`;
  if (f.t === 'number' && Number(s) < 0) return `${f.label} cannot be negative.`;
  if (f.t === 'number' && !Number.isFinite(Number(s))) return `${f.label} must be a number.`;
  return null;
}

/** Thrown from `validate`/`onSubmit` to attach a message to a specific field. */
export class FieldError extends Error {
  readonly field: string;
  constructor(field: string, message: string) {
    super(message);
    this.field = field;
  }
}

/* ---------- component ---------- */

export interface FormProps {
  fields: Field[];
  initial?: Record<string, unknown>;
  submitLabel?: string;
  /** extra client checks; return a message (or throw FieldError) to stop */
  validate?: (v: FormValues) => string | null | undefined;
  /** performs the API call; resolves to an optional toast message */
  onSubmit: (v: FormValues) => Promise<string | void>;
  onDone: (message?: string) => void;
  onCancel: () => void;
  danger?: boolean;
  /** server field name → form key, for API fields named differently from the input (e.g. qp_file_id → qp_file) */
  fieldAliases?: Record<string, string>;
}

const domId = (base: string, k: string) => base + '_' + k.replace(/[^A-Za-z0-9_-]/g, '_');

export function Form({ fields, initial = {}, submitLabel = 'Save', validate, onSubmit, onDone, onCancel, danger, fieldAliases }: FormProps) {
  const base = useId().replace(/:/g, '');
  const [values, setValues] = useState<FormValues>(() => {
    const v: FormValues = {};
    for (const f of fields) if (!isSection(f) && f.t !== 'static') v[f.k] = normalize(f, initial[f.k]);
    return v;
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [topError, setTopError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(0);
  const errRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (topError) errRef.current?.scrollIntoView({ block: 'nearest' });
  }, [topError]);

  const visible = (f: Field) => !f.when || f.when(values);
  const inputs = fields.filter((f): f is InputField => !isSection(f) && f.t !== 'static');

  const set = (k: string, x: FormValue) => {
    setValues((prev) => ({ ...prev, [k]: x }));
    setErrors((prev) => {
      if (!prev[k]) return prev;
      const n = { ...prev };
      delete n[k];
      return n;
    });
  };

  const focusField = (k: string) => {
    const el = document.getElementById(domId(base, k));
    const target = el?.matches('input,select,textarea') ? el : el?.querySelector<HTMLElement>('input,select,textarea');
    target?.focus();
  };

  const showError = (message: string, serverField?: string) => {
    setTopError(message);
    const field = serverField && fieldAliases?.[serverField] ? fieldAliases[serverField] : serverField;
    if (field) {
      const match = inputs.find((f) => visible(f) && (f.k === field || f.k.split('.').pop() === field || f.k === field.split('.').pop()));
      if (match) {
        setErrors({ [match.k]: message });
        window.setTimeout(() => focusField(match.k), 0);
        return;
      }
    }
    setErrors({});
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy || uploading) return;
    for (const f of inputs) {
      if (!visible(f)) continue;
      const m = checkField(f, values[f.k]);
      if (m) return showError(m, f.k);
    }
    try {
      const m = validate?.(values);
      if (m) return showError(m);
    } catch (err) {
      if (err instanceof FieldError) return showError(err.message, err.field);
      throw err;
    }
    setBusy(true);
    setTopError(null);
    try {
      const msg = await onSubmit(values);
      onDone(msg || undefined);
    } catch (err) {
      if (err instanceof FieldError) showError(err.message, err.field);
      else {
        const ae = toApiError(err);
        showError(ae.message, ae.field);
      }
      setBusy(false);
    }
  };

  const onFiles = async (f: InputField, list: FileList | null) => {
    const files = list ? Array.from(list) : [];
    if (!files.length) return;
    setUploading((n) => n + 1);
    try {
      for (const file of files) {
        const ref = await uploadFile(file);
        setValues((prev) => ({ ...prev, [f.k]: f.multiple ? [...vf(prev, f.k), ref] : [ref] }));
      }
      setErrors((prev) => ({ ...prev, [f.k]: '' }));
    } catch (err) {
      setErrors((prev) => ({ ...prev, [f.k]: toApiError(err).message }));
    } finally {
      setUploading((n) => n - 1);
    }
  };

  const renderInput = (f: InputField): ReactNode => {
    const id = domId(base, f.k);
    const err = errors[f.k];
    const describedBy = [f.hint ? id + '_h' : '', err ? id + '_e' : ''].filter(Boolean).join(' ') || undefined;
    const common = { id, name: f.k, 'aria-invalid': err ? true : undefined, 'aria-describedby': describedBy } as const;
    const v = values[f.k];
    switch (f.t) {
      case 'select':
        return (
          <select {...common} value={typeof v === 'string' ? v : ''} onChange={(e) => set(f.k, e.target.value)}>
            <option value="">Select…</option>
            {(f.o ?? []).map((o) => (
              <option key={optVal(o)} value={optVal(o)}>
                {optLabel(o)}
              </option>
            ))}
          </select>
        );
      case 'multi': {
        const cur = va(values, f.k);
        return (
          <div className="chips" id={id} role="group" aria-labelledby={id + '_l'} aria-describedby={describedBy}>
            {(f.o ?? []).map((o) => {
              const val = optVal(o);
              return (
                <label className="chip" key={val}>
                  <input type="checkbox" name={f.k} value={val} checked={cur.includes(val)} onChange={(e) => set(f.k, e.target.checked ? [...cur, val] : cur.filter((x) => x !== val))} />
                  <span>{optLabel(o)}</span>
                </label>
              );
            })}
            {!(f.o ?? []).length && <span className="muted">No options available.</span>}
          </div>
        );
      }
      case 'textarea':
        return <textarea {...common} rows={f.rows ?? 3} value={typeof v === 'string' ? v : ''} onChange={(e) => set(f.k, e.target.value)} placeholder={f.ph} />;
      case 'file': {
        const cur = vf(values, f.k);
        return (
          <>
            <input {...common} type="file" multiple={f.multiple} accept={f.accept ?? '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip,.jpg,.png'} onChange={(e) => { const fl = e.target.files; void onFiles(f, fl); e.target.value = ''; }} />
            {uploading > 0 && <span className="uploading">Uploading…</span>}
            {cur.length > 0 && (
              <div className="files">
                {cur.map((x) => (
                  <span className="file" key={String(x.id)}>
                    {x.name}
                    <button type="button" className="rm" aria-label={'Remove ' + x.name} onClick={() => set(f.k, cur.filter((y) => y.id !== x.id))}>
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </>
        );
      }
      default: {
        const t = f.t ?? 'text';
        return (
          <input
            {...common}
            type={t}
            value={typeof v === 'string' ? v : ''}
            onChange={(e) => set(f.k, f.pin ? e.target.value.replace(/\D/g, '').slice(0, 4) : e.target.value)}
            placeholder={f.ph}
            autoComplete={f.autoComplete ?? (t === 'password' ? 'new-password' : undefined)}
            inputMode={t === 'number' || f.pin || f.pincode ? 'numeric' : t === 'tel' ? 'tel' : undefined}
            min={t === 'number' ? 0 : undefined}
            maxLength={f.pin ? 4 : f.pincode ? 6 : undefined}
          />
        );
      }
    }
  };

  const renderField = (f: Field, i: number): ReactNode => {
    if (!visible(f)) return null;
    if (isSection(f)) {
      return (
        <div className="fsec" key={'s' + i}>
          <h4>{f.sec}</h4>
          {f.hint && <p>{f.hint}</p>}
        </div>
      );
    }
    const id = domId(base, f.k);
    const wide = f.wide || f.t === 'multi' || f.t === 'textarea' || f.t === 'static';
    const star = f.req ? <span className="req" aria-hidden="true"> *</span> : null;
    const err = errors[f.k];
    return (
      <div className={'field' + (wide ? ' wide' : '') + (err ? ' err' : '')} key={f.k}>
        {f.t === 'multi' || f.t === 'static' ? (
          <span className="lab" id={id + '_l'}>
            {f.label}
            {star}
          </span>
        ) : (
          <label htmlFor={id}>
            {f.label}
            {star}
            {f.req && <span className="sr-only"> (required)</span>}
          </label>
        )}
        {f.t === 'static' ? <div className="static">{f.html ?? '—'}</div> : renderInput(f)}
        {f.hint && <small id={id + '_h'}>{f.hint}</small>}
        {err && (
          <span className="ferr-i" id={id + '_e'}>
            {err}
          </span>
        )}
      </div>
    );
  };

  return (
    <form onSubmit={submit} noValidate>
      <div className="fgrid">{fields.map(renderField)}</div>
      {topError && (
        <p className="ferr" role="alert" ref={errRef} style={{ marginTop: 14 }}>
          {topError}
        </p>
      )}
      <div className="mfoot" style={{ marginTop: 14 }}>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className={'btn ' + (danger ? 'danger' : 'primary')} disabled={busy || uploading > 0} aria-busy={busy}>
          {busy ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}
