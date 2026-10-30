/*
 * Book-order and academic-pack field specs.
 * Used by Marketing (PUT /requests/<id>/order, POST …/dist-order/accept) and by distributors
 * (POST/PUT …/dist-order, POST /direct-orders).
 */
import { addDays, nowLocal, numOrNull, today } from '../format';
import type { DistOrder, Meta, RequestDetail } from '../types';
import { fileIds, va, vs, type Field, type FormValues } from '../ui/Form';

export const CONF_ST = ['Order Confirmed', 'Partially Confirmed'];
export const isConfirmed = (v: FormValues) => CONF_ST.includes(vs(v, 'order_status'));

const seriesNames = (meta: Meta) => meta.series.map((s) => s.name);

/* ---------- academic support pack ---------- */

export function packFields(meta: Meta, when?: (v: FormValues) => boolean): Field[] {
  const both = (extra?: (v: FormValues) => boolean) => (v: FormValues) => (!when || when(v)) && (!extra || extra(v));
  return [
    { sec: 'Academic support', hint: 'Created with the order: a teacher-training session, question-paper requests, and access to the manuals for the ordered series.', when: both() },
    { k: 'pack.training_at', label: 'Preferred training date & time', t: 'datetime-local', req: true, when: both() },
    { k: 'pack.training_mode', label: 'Training mode', t: 'select', o: ['Offline', 'Online'], req: true, when: both() },
    { k: 'pack.teachers', label: 'Teachers who will attend', t: 'number', req: true, when: both() },
    { k: 'pack.venue', label: 'Training venue (offline)', t: 'textarea', rows: 2, hint: 'Leave blank to use the school address', when: both((v) => vs(v, 'pack.training_mode') !== 'Online') },
    { k: 'pack.link', label: 'Meeting link (online, if available)', t: 'url', ph: 'https://', hint: 'Without a link, Myjo adds one before the session is shared', when: both((v) => vs(v, 'pack.training_mode') === 'Online') },
    { k: 'pack.exams', label: 'Question papers needed', t: 'multi', o: meta.exam_types, req: true, when: both() },
    { k: 'pack.papers_by', label: 'First question papers needed by', t: 'date', req: true, when: both() },
  ];
}

export const packDefaults = () => ({ 'pack.training_mode': 'Offline', 'pack.exams': ['Unit Test', 'Term Exam'], 'pack.papers_by': addDays(30) });

export function packProblem(v: FormValues): string | null {
  if (!vs(v, 'pack.training_at')) return 'Enter the preferred training date & time.';
  if (vs(v, 'pack.training_at') < nowLocal()) return 'Preferred training date & time must be in the future.';
  if (!vs(v, 'pack.training_mode')) return 'Choose the training mode.';
  if (!(Number(vs(v, 'pack.teachers')) > 0)) return 'Enter how many teachers will attend the training.';
  if (!va(v, 'pack.exams').length) return 'Choose the question papers needed.';
  if (!vs(v, 'pack.papers_by')) return 'Enter when the first question papers are needed.';
  if (vs(v, 'pack.papers_by') < today()) return 'Question papers needed-by date cannot be in the past.';
  return null;
}

export function packBody(v: FormValues) {
  const online = vs(v, 'pack.training_mode') === 'Online';
  return {
    training_at: vs(v, 'pack.training_at'),
    training_mode: vs(v, 'pack.training_mode'),
    teachers: numOrNull(vs(v, 'pack.teachers')),
    ...(online ? { link: vs(v, 'pack.link') } : { venue: vs(v, 'pack.venue') }),
    exams: va(v, 'pack.exams'),
    papers_by: vs(v, 'pack.papers_by'),
  };
}

/** A pack is needed when the school is not converted yet and no pack exists. */
export const needsPack = (r: RequestDetail) => !r.academic?.pack && r.status !== 'Converted';

/* ---------- order fields ---------- */

export function orderBody(v: FormValues) {
  return {
    ay: vs(v, 'ay'),
    po: vs(v, 'po'),
    series: va(v, 'series'),
    classes: va(v, 'classes'),
    subjects: va(v, 'subjects'),
    qty: numOrNull(vs(v, 'qty')),
    conf_date: vs(v, 'conf_date') || null,
    del_date: vs(v, 'del_date') || null,
    payment: vs(v, 'payment'),
    remarks: vs(v, 'remarks'),
  };
}

/** Final order entered by a distributor (or accepted by Marketing): every field required. */
export function finalOrderFields(meta: Meta, withFiles: boolean): Field[] {
  return [
    { k: 'order_status', label: 'Order status', t: 'select', o: meta.confirmed_statuses, req: true },
    { k: 'ay', label: 'Academic year', t: 'select', o: meta.academic_years, req: true },
    { k: 'po', label: 'PO / reference no.', req: true },
    { k: 'series', label: 'Book series', t: 'multi', o: seriesNames(meta), req: true },
    { k: 'classes', label: 'Classes', t: 'multi', o: meta.classes, req: true },
    { k: 'subjects', label: 'Subjects', t: 'multi', o: meta.subjects, req: true },
    { k: 'qty', label: 'Quantity ordered (books)', t: 'number', req: true },
    { k: 'conf_date', label: 'Order confirmation date', t: 'date', req: true },
    { k: 'del_date', label: 'Expected delivery date', t: 'date', req: true },
    { k: 'payment', label: 'Payment status', t: 'select', o: meta.payment_statuses, req: true },
    ...(withFiles ? [{ k: 'files', label: 'PO copy', t: 'file', accept: '.pdf,.jpg,.png,.doc,.docx,.xls,.xlsx' } as Field] : []),
    { k: 'remarks', label: 'Order remarks', t: 'textarea', rows: 2 },
  ];
}

export function orderProblem(v: FormValues): string | null {
  if (!(Number(vs(v, 'qty')) > 0)) return 'Quantity must be greater than zero.';
  if (vs(v, 'conf_date') > today()) return 'Confirmation date cannot be in the future.';
  if (vs(v, 'del_date') < vs(v, 'conf_date')) return 'Expected delivery cannot be before the confirmation date.';
  return null;
}

/** Prefill a final order from the distributor's submitted order, else from the request. */
export function orderPrefill(r: RequestDetail, q: DistOrder | null): Record<string, unknown> {
  const src = q && q.status !== 'Rejected' ? q : null;
  return {
    ay: src?.ay ?? r.ay,
    po: src?.po ?? '',
    series: src?.series ?? r.series,
    classes: src?.classes ?? r.classes,
    subjects: src?.subjects ?? r.subjects,
    qty: src?.qty ?? r.marketing?.exp_qty ?? r.exp_qty,
    del_date: src?.req_delivery ?? '',
    files: src?.files ?? [],
    remarks: src?.remarks ?? '',
    conf_date: today(),
    payment: 'Pending',
    order_status: r.order_status && CONF_ST.includes(r.order_status) ? r.order_status : 'Order Confirmed',
  };
}

/** Final-order body: order fields plus the optional confirmed status (defaults to Order Confirmed on the server). */
export function finalOrderBody(v: FormValues) {
  return { ...orderBody(v), order_status: vs(v, 'order_status') || 'Order Confirmed' };
}

/* ---------- Marketing: order status ---------- */

const NEED: [string, string][] = [
  ['ay', 'Academic year'], ['po', 'PO / reference no.'], ['series', 'Book series'], ['classes', 'Classes'], ['subjects', 'Subjects'],
  ['qty', 'Quantity ordered'], ['conf_date', 'Confirmation date'], ['del_date', 'Expected delivery date'], ['payment', 'Payment status'],
];

export function orderStatusFields(meta: Meta, r: RequestDetail, withPack: boolean): Field[] {
  return [
    { k: 'order_status', label: 'Order status', t: 'select', o: meta.order_statuses, req: true },
    { sec: 'Confirmed order details', hint: 'All fields are required to confirm an order.', when: isConfirmed },
    { k: '_school', label: 'School', t: 'static', html: r.school.name, when: isConfirmed },
    { k: '_dist', label: 'Distributor', t: 'static', html: r.distributor?.name, when: isConfirmed },
    { k: 'ay', label: 'Academic year', t: 'select', o: meta.academic_years, when: isConfirmed },
    { k: 'po', label: 'Purchase order / reference no.', when: isConfirmed },
    { k: 'series', label: 'Book series', t: 'multi', o: seriesNames(meta), when: isConfirmed },
    { k: 'classes', label: 'Classes', t: 'multi', o: meta.classes, when: isConfirmed },
    { k: 'subjects', label: 'Subjects', t: 'multi', o: meta.subjects, when: isConfirmed },
    { k: 'qty', label: 'Quantity ordered', t: 'number', when: isConfirmed },
    { k: 'conf_date', label: 'Order confirmation date', t: 'date', when: isConfirmed },
    { k: 'del_date', label: 'Expected delivery date', t: 'date', when: isConfirmed },
    { k: 'payment', label: 'Payment status', t: 'select', o: meta.payment_statuses, when: isConfirmed },
    { k: 'remarks', label: 'Remarks', t: 'textarea', rows: 2, when: isConfirmed },
    ...(withPack ? packFields(meta, isConfirmed) : []),
  ];
}

export function orderStatusCheck(v: FormValues, withPack: boolean): string | null {
  if (!isConfirmed(v)) return null;
  for (const [k, label] of NEED) {
    const x = v[k];
    if (x === undefined || x === '' || (Array.isArray(x) && !x.length)) return `${label} is required to confirm the order.`;
  }
  if (!(Number(vs(v, 'qty')) > 0)) return 'Quantity ordered must be greater than zero.';
  if (vs(v, 'del_date') < vs(v, 'conf_date')) return 'Expected delivery cannot be before the confirmation date.';
  return withPack ? packProblem(v) : null;
}

export function orderStatusInitial(r: RequestDetail): Record<string, unknown> {
  const o = r.order;
  const base = o
    ? { ...o }
    : { ay: r.ay, series: r.series, classes: r.classes, subjects: r.subjects, qty: r.marketing?.exp_qty ?? r.exp_qty, payment: 'Pending' };
  return { ...packDefaults(), ...base, order_status: r.order_status ?? '' };
}

/* ---------- Distributor: non-final order (Marketing confirms) ---------- */

export function placeOrderFields(meta: Meta, schoolLabel: string): Field[] {
  return [
    { k: '_school', label: 'School', t: 'static', html: schoolLabel },
    { k: 'ay', label: 'Academic year', t: 'select', o: meta.academic_years, req: true },
    { k: 'po', label: 'Distributor PO / reference no.', req: true },
    { k: 'series', label: 'Book series', t: 'multi', o: seriesNames(meta), req: true },
    { k: 'classes', label: 'Classes', t: 'multi', o: meta.classes, req: true },
    { k: 'subjects', label: 'Subjects', t: 'multi', o: meta.subjects, req: true },
    { k: 'qty', label: 'Total quantity (books)', t: 'number', req: true },
    { k: 'del_date', label: 'Required delivery date', t: 'date', req: true },
    { k: 'files', label: 'PO copy', t: 'file', accept: '.pdf,.jpg,.png,.doc,.docx,.xls,.xlsx' },
    { k: 'remarks', label: 'Remarks', t: 'textarea', rows: 2 },
  ];
}

export function placeOrderCheck(v: FormValues): string | null {
  if (!(Number(vs(v, 'qty')) > 0)) return 'Quantity must be greater than zero.';
  if (vs(v, 'del_date') < today()) return 'Required delivery date cannot be in the past.';
  return null;
}

/**
 * Order sent for Myjo review. The server validates every order with the same rules, so the
 * required delivery date travels as `del_date` (stored as `req_delivery`) and the confirmation
 * date / payment are sent as today / Pending; Marketing sets the real values when accepting.
 */
export function placeOrderBody(v: FormValues) {
  return {
    ay: vs(v, 'ay'), po: vs(v, 'po'), series: va(v, 'series'), classes: va(v, 'classes'), subjects: va(v, 'subjects'),
    qty: numOrNull(vs(v, 'qty')), conf_date: today(), del_date: vs(v, 'del_date'), payment: 'Pending',
    remarks: vs(v, 'remarks'), file_ids: fileIds(v, 'files'),
  };
}
