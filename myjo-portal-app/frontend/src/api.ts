/*
 * Thin fetch wrapper for the Myjo API.
 * - Base path `/api` (proxied to Flask in development, see vite.config.ts).
 * - Bearer token kept in memory and mirrored to sessionStorage (so a page reload keeps the session
 *   for this tab only). Storage access is wrapped because it can throw in private windows.
 * - Every non-2xx response becomes an ApiError carrying the server's `error` and `field`.
 * - A 401 on any call except login clears the session and notifies the auth layer.
 */
import type { FileRef, ListResponse } from './types';

const BASE = '/api';
const STORAGE_KEY = 'myjo-session';

export interface Session {
  token: string;
  must_change: boolean;
}

function readStored(): Session | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === 'object' && typeof (parsed as { token?: unknown }).token === 'string') {
      const p = parsed as { token: string; must_change?: unknown };
      return { token: p.token, must_change: p.must_change === true };
    }
  } catch {
    /* storage unavailable or corrupt: start signed out */
  }
  return null;
}

let session: Session | null = readStored();
let unauthorizedHandler: (() => void) | null = null;

export function getSession(): Session | null {
  return session;
}

export function setSession(next: Session | null): void {
  session = next;
  try {
    if (next) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* memory copy is enough */
  }
}

/** The auth provider registers this so an expired token signs the user out. */
export function onUnauthorized(fn: (() => void) | null): void {
  unauthorizedHandler = fn;
}

export class ApiError extends Error {
  readonly status: number;
  readonly field?: string;
  constructor(message: string, status: number, field?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.field = field;
  }
}

export function toApiError(e: unknown): ApiError {
  if (e instanceof ApiError) return e;
  if (e instanceof Error) return new ApiError(e.message, 0);
  return new ApiError('Something went wrong.', 0);
}

export type QueryValue = string | number | boolean | null | undefined;
export type Query = Record<string, QueryValue>;

export function qs(query?: Query): string {
  if (!query) return '';
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? '?' + s : '';
}

const FALLBACK: Record<number, string> = {
  0: 'Cannot reach the server. Check your connection and try again.',
  400: 'Please check the details and try again.',
  401: 'Your session has ended. Please sign in again.',
  403: 'You are not allowed to do this.',
  404: 'This record was not found.',
  409: 'This conflicts with the current state of the record.',
  423: 'This account is locked. Try again later or ask Admin to unlock it.',
};

async function errorFrom(res: Response): Promise<ApiError> {
  let message = FALLBACK[res.status] ?? 'The server could not complete the request. Try again.';
  let field: string | undefined;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === 'object') {
      const b = body as { error?: unknown; field?: unknown };
      if (typeof b.error === 'string' && b.error) message = b.error;
      if (typeof b.field === 'string' && b.field) field = b.field;
    }
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(message, res.status, field);
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  query?: Query;
}

async function send(path: string, opts: RequestOptions = {}): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (session) headers.Authorization = 'Bearer ' + session.token;
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) body = opts.body;
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }
  let res: Response;
  try {
    res = await fetch(BASE + path + qs(opts.query), { method: opts.method ?? 'GET', headers, body });
  } catch {
    throw new ApiError(FALLBACK[0], 0);
  }
  if (!res.ok) {
    const err = await errorFrom(res);
    if (res.status === 401 && path !== '/auth/login' && session) {
      setSession(null);
      unauthorizedHandler?.();
    }
    throw err;
  }
  return res;
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(path, opts);
  const text = await res.text();
  // The fetch boundary: JSON is trusted to match the declared type.
  return (text ? JSON.parse(text) : undefined) as T;
}

export const get = <T>(path: string, query?: Query) => api<T>(path, { query });
export const post = <T>(path: string, body: unknown = {}) => api<T>(path, { method: 'POST', body });
export const put = <T>(path: string, body: unknown = {}) => api<T>(path, { method: 'PUT', body });
export const del = <T>(path: string) => api<T>(path, { method: 'DELETE' });

/** Accepts either a bare array or the `{items,total}` list envelope. */
export function asList<T>(x: T[] | ListResponse<T> | null | undefined): T[] {
  if (!x) return [];
  return Array.isArray(x) ? x : x.items ?? [];
}

export function uploadFile(file: File): Promise<FileRef> {
  const fd = new FormData();
  fd.append('file', file);
  return api<FileRef>('/files', { method: 'POST', body: fd });
}

function filenameFrom(res: Response, fallback: string): string {
  const cd = res.headers.get('Content-Disposition') || '';
  const star = /filename\*=UTF-8''([^;]+)/i.exec(cd);
  if (star) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      /* fall through */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(cd);
  return plain ? plain[1] : fallback;
}

/** Downloads an authenticated file: fetch → blob → object URL → temporary link click. */
export async function download(path: string, query: Query | undefined, fallbackName: string): Promise<void> {
  const res = await send(path, { query });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filenameFrom(res, fallbackName);
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 4000);
}

/** `context` is required for school users (paper:<id>:qp|ak, resource:<id>); staff may omit it. */
export function downloadFile(file: { id: string | number; name: string }, context?: string): Promise<void> {
  return download(`/files/${encodeURIComponent(String(file.id))}/download`, context ? { context } : undefined, file.name);
}
