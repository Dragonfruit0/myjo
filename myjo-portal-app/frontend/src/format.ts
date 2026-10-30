/* Display helpers shared by every screen (dates, numbers, names). */
import type { Id } from './types';

export const pad = (n: number, l = 2) => String(n).padStart(l, '0');

const toDate = (s: string) => new Date(s.length === 10 ? s + 'T00:00' : s);

export function isoDate(d: Date): string {
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
}

export const today = () => isoDate(new Date());

export function nowLocal(): string {
  const d = new Date();
  return isoDate(d) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
}

export function addDays(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return isoDate(d);
}

/** 12 Mar 2026 */
export function fd(s?: string | null): string {
  if (!s) return '—';
  const d = toDate(s.slice(0, 10));
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

/** 12 Mar 2026, 11:00 am */
export function fdt(s?: string | null): string {
  if (!s) return '—';
  if (s.length <= 10) return fd(s);
  const d = toDate(s.slice(0, 16));
  if (Number.isNaN(d.getTime())) return s;
  return fd(s) + ', ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

export const timeOf = (s?: string | null) => (s && s.length > 10 ? s.slice(11, 16) : '');

export function daysBetween(a: string, b: string): number {
  return Math.round((toDate(b.slice(0, 10)).getTime() - toDate(a.slice(0, 10)).getTime()) / 864e5);
}

export const list = (a?: readonly string[] | null) => (a && a.length ? a.join(', ') : '—');

export function num(n: unknown): string {
  if (n === '' || n === null || n === undefined) return '—';
  const v = Number(n);
  return Number.isFinite(v) ? v.toLocaleString('en-IN') : String(n);
}

export const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;

/** API fields such as `school` or `distributor` may be a name or an object with a name. */
export function nameOf(x: unknown): string {
  if (typeof x === 'string') return x;
  if (x && typeof x === 'object' && 'name' in x) {
    const n = (x as { name: unknown }).name;
    return typeof n === 'string' ? n : '';
  }
  return '';
}

export function fileSize(b?: number): string {
  if (!b) return '';
  return b >= 1048576 ? (b / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB';
}

export const stars = (n: number) => '★'.repeat(Math.max(0, Math.min(5, n))) + '☆'.repeat(5 - Math.max(0, Math.min(5, n)));

/** Select values are strings; send numeric ids back as numbers. */
export function toId(s: string): Id {
  return /^\d+$/.test(s) ? Number(s) : s;
}

export function numOrNull(s: string | undefined): number | null {
  if (s === undefined || s.trim() === '') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}
