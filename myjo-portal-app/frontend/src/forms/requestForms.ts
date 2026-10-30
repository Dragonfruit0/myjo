/*
 * Field specs + request bodies for the demo-request workflow (labels and messages follow the prototype).
 * Keys equal API field names so server `field` errors attach to the right input.
 */
import { nowLocal, numOrNull, toId, today } from '../format';
import type { Meta, RequestDetail } from '../types';
import { fileIds, va, vs, type Field, type FormValues } from '../ui/Form';

/* ---------- school block (shared by demo requests and direct orders) ---------- */

export function schoolFields(meta: Meta, withAy: boolean): Field[] {
  return [
    { sec: 'School' },
    { k: 'school.name', label: 'School name', req: true, wide: true },
    { k: 'school.address', label: 'School address', req: true, wide: true },
    { k: 'school.city', label: 'City', req: true },
    { k: 'school.state', label: 'State', req: true },
    { k: 'school.pincode', label: 'Pincode', req: true, pincode: true, ph: '6 digits' },
    { k: 'school.board', label: 'School board', t: 'select', o: meta.boards, req: true },
    ...(withAy ? [{ k: 'ay', label: 'Academic year', t: 'select', o: meta.academic_years, req: true } as Field] : []),
    { k: 'school.strength', label: 'Approx. student strength', t: 'number' },
    { sec: 'Contact person' },
    { k: 'school.contact', label: 'Contact person name', req: true },
    { k: 'school.designation', label: 'Designation', req: true },
    { k: 'school.mobile', label: 'Mobile number', t: 'tel', req: true },
    { k: 'school.email', label: 'Email address', t: 'email', req: true },
  ];
}

export function schoolBody(v: FormValues) {
  return {
    name: vs(v, 'school.name'),
    address: vs(v, 'school.address'),
    city: vs(v, 'school.city'),
    state: vs(v, 'school.state'),
    pincode: vs(v, 'school.pincode'),
    board: vs(v, 'school.board'),
    strength: numOrNull(vs(v, 'school.strength')),
    contact: vs(v, 'school.contact'),
    designation: vs(v, 'school.designation'),
    mobile: vs(v, 'school.mobile'),
    email: vs(v, 'school.email'),
  };
}

export function distributorField(meta: Meta, isDist: boolean, ownLabel: string): Field {
  return isDist
    ? { k: '_dist', label: 'Distributor', t: 'static', html: ownLabel }
    : { k: 'distributor_id', label: 'Distributor', t: 'select', o: meta.distributors.map((d) => [String(d.id), `${d.name} · ${d.phone}`] as const), req: true };
}

/* ---------- demo request ---------- */

export function requestFields(meta: Meta, isDist: boolean, ownLabel: string): Field[] {
  return [
    ...schoolFields(meta, true),
    { sec: 'Requirement' },
    { k: 'classes', label: 'Classes / grades required', t: 'multi', o: meta.classes, req: true },
    { k: 'subjects', label: 'Subjects required', t: 'multi', o: meta.subjects, req: true },
    { k: 'series', label: 'Myjo book series of interest', t: 'multi', o: meta.series.map((s) => s.name), req: true },
    { k: 'exp_qty', label: 'Expected order quantity', t: 'number' },
    { k: 'pref_date', label: 'Preferred demo date', t: 'date', req: true },
    { k: 'pref_time', label: 'Preferred demo time', t: 'time', req: true },
    { sec: 'Distributor' },
    distributorField(meta, isDist, ownLabel),
    { k: 'remarks', label: 'Remarks', t: 'textarea' },
  ];
}

export function requestInitial(r: RequestDetail | null, meta: Meta): Record<string, unknown> {
  if (!r) return { ay: meta.academic_years[meta.academic_years.length - 1] ?? '', pref_time: '11:00' };
  const s = r.school;
  return {
    'school.name': s.name, 'school.address': s.address, 'school.city': s.city, 'school.state': s.state,
    'school.pincode': s.pincode, 'school.board': s.board, 'school.strength': s.strength,
    'school.contact': s.contact, 'school.designation': s.designation, 'school.mobile': s.mobile, 'school.email': s.email,
    ay: r.ay, classes: r.classes, subjects: r.subjects, series: r.series, exp_qty: r.exp_qty,
    pref_date: r.pref_date, pref_time: r.pref_time, distributor_id: r.distributor?.id, remarks: r.remarks,
  };
}

export function requestBody(v: FormValues, isDist: boolean) {
  return {
    school: schoolBody(v),
    ay: vs(v, 'ay'),
    classes: va(v, 'classes'),
    subjects: va(v, 'subjects'),
    series: va(v, 'series'),
    exp_qty: numOrNull(vs(v, 'exp_qty')),
    pref_date: vs(v, 'pref_date'),
    pref_time: vs(v, 'pref_time'),
    ...(isDist ? {} : { distributor_id: toId(vs(v, 'distributor_id')) }),
    remarks: vs(v, 'remarks'),
  };
}

export const newRequestCheck = (v: FormValues) => (vs(v, 'pref_date') < today() ? 'Preferred demo date cannot be in the past.' : null);

/* ---------- demo schedule ---------- */

export function scheduleFields(meta: Meta): Field[] {
  const online = (v: FormValues) => vs(v, 'mode') === 'Online';
  const offline = (v: FormValues) => vs(v, 'mode') === 'Offline';
  return [
    { k: 'at', label: 'Demo date & time', t: 'datetime-local', req: true },
    { k: 'mode', label: 'Demo mode', t: 'select', o: ['Online', 'Offline'], req: true },
    { k: 'presenter', label: 'Myjo presenter', t: 'select', o: meta.people.demo, req: true },
    { k: 'marketing', label: 'Marketing person', t: 'select', o: meta.people.mkt, req: true },
    { sec: 'Online demo', hint: 'Required when mode is Online', when: online },
    { k: 'platform', label: 'Platform', t: 'select', o: ['Zoom', 'Google Meet', 'Microsoft Teams'], when: online },
    { k: 'link', label: 'Meeting link', t: 'url', ph: 'https://', when: online },
    { sec: 'Offline demo', hint: 'Required when mode is Offline', when: offline },
    { k: 'venue', label: 'Venue details', t: 'textarea', rows: 2, when: offline },
    { sec: 'Plan' },
    { k: 'agenda', label: 'Demo agenda', t: 'textarea' },
    { k: 'instructions', label: 'Special instructions / remarks', t: 'textarea', rows: 2 },
  ];
}

export function scheduleInitial(r: RequestDetail): Record<string, unknown> {
  if (r.schedule) return { ...r.schedule };
  return { at: r.pref_date ? `${r.pref_date}T${r.pref_time || '11:00'}` : '', mode: 'Online', presenter: r.assigned_to ?? '' };
}

export function scheduleCheck(v: FormValues): string | null {
  if (vs(v, 'at') < nowLocal()) return 'Demo date & time must be in the future.';
  if (vs(v, 'mode') === 'Online' && (!vs(v, 'platform') || !vs(v, 'link'))) return 'Choose a platform and enter the meeting link for an online demo.';
  if (vs(v, 'mode') === 'Offline' && !vs(v, 'venue')) return 'Enter venue details for an offline demo.';
  return null;
}

export function scheduleBody(v: FormValues) {
  const online = vs(v, 'mode') === 'Online';
  return {
    at: vs(v, 'at'),
    mode: vs(v, 'mode'),
    presenter: vs(v, 'presenter'),
    marketing: vs(v, 'marketing'),
    platform: online ? vs(v, 'platform') : '',
    link: online ? vs(v, 'link') : '',
    venue: online ? '' : vs(v, 'venue'),
    agenda: vs(v, 'agenda'),
    instructions: vs(v, 'instructions'),
  };
}

/* ---------- Myjo demo feedback ---------- */

export const REQUESTED = ['Samples', 'Brochures', 'Quotation', 'Presentation'];

export function feedbackFields(meta: Meta): Field[] {
  return [
    { k: 'by', label: 'Demo conducted by', t: 'select', o: meta.people.demo, req: true },
    { k: 'date', label: 'Date of demo', t: 'date', req: true },
    { k: 'attendees', label: 'Persons attended from the school', req: true, wide: true },
    { k: 'designations', label: 'Designations of attendees', wide: true },
    { k: 'classes', label: 'Classes discussed', t: 'multi', o: meta.classes },
    { k: 'subjects', label: 'Subjects discussed', t: 'multi', o: meta.subjects },
    { k: 'series', label: 'Myjo book series demonstrated', t: 'multi', o: meta.series.map((s) => s.name), req: true },
    { k: 'interest', label: 'Interest level', t: 'select', o: ['High', 'Medium', 'Low'], req: true },
    { k: 'competitor', label: 'Competitor publisher currently used' },
    { k: 'requirements', label: 'School requirements', t: 'textarea' },
    { k: 'requested', label: 'Requested by school', t: 'multi', o: REQUESTED },
    { k: 'objections', label: 'Questions, objections or concerns', t: 'textarea' },
    { k: 'next_follow', label: 'Next follow-up date', t: 'date' },
    { k: 'remarks', label: 'Internal remarks', t: 'textarea' },
    { k: 'files', label: 'Brochures, presentations, quotations, sample details, requirement documents', t: 'file', multiple: true, wide: true },
  ];
}

export function feedbackInitial(r: RequestDetail): Record<string, unknown> {
  if (r.feedback) return { ...r.feedback };
  return { by: r.schedule?.presenter, date: r.schedule?.at?.slice(0, 10), classes: r.classes, subjects: r.subjects, series: r.series };
}

export const feedbackCheck = (v: FormValues) => (vs(v, 'date') > today() ? 'Date of demo cannot be in the future.' : null);

export function feedbackBody(v: FormValues) {
  return {
    by: vs(v, 'by'), date: vs(v, 'date'), attendees: vs(v, 'attendees'), designations: vs(v, 'designations'),
    classes: va(v, 'classes'), subjects: va(v, 'subjects'), series: va(v, 'series'), interest: vs(v, 'interest'),
    requirements: vs(v, 'requirements'), requested: va(v, 'requested'), objections: vs(v, 'objections'),
    competitor: vs(v, 'competitor'), next_follow: vs(v, 'next_follow') || null, remarks: vs(v, 'remarks'),
    file_ids: fileIds(v, 'files'),
  };
}

/* ---------- marketing feedback ---------- */

export function marketingFields(meta: Meta): Field[] {
  return [
    { k: 'potential', label: 'School potential', t: 'select', o: ['High', 'Medium', 'Low'], req: true },
    { k: 'person', label: 'Assigned marketing person', t: 'select', o: meta.people.mkt, req: true },
    { k: 'dm_name', label: 'Decision-maker name', req: true },
    { k: 'dm_desig', label: 'Decision-maker designation' },
    { k: 'dm_mobile', label: 'Decision-maker mobile', t: 'tel' },
    { k: 'dm_email', label: 'Decision-maker email', t: 'email' },
    { k: 'competitor', label: 'Existing publisher / competitor' },
    { k: 'stage', label: 'Current discussion stage', t: 'select', o: meta.discussion_stages },
    { k: 'exp_qty', label: 'Expected order quantity', t: 'number' },
    { k: 'decision_date', label: 'Expected decision date', t: 'date' },
    { k: 'next_follow', label: 'Next follow-up date', t: 'date' },
    { k: 'next_action', label: 'Next action', wide: true },
    { k: 'remarks', label: 'Marketing remarks', t: 'textarea' },
  ];
}

export function marketingInitial(r: RequestDetail): Record<string, unknown> {
  if (r.marketing) return { ...r.marketing };
  return {
    potential: r.feedback?.interest, dm_name: r.school.contact, dm_desig: r.school.designation, dm_mobile: r.school.mobile,
    dm_email: r.school.email, competitor: r.feedback?.competitor, exp_qty: r.exp_qty, person: r.schedule?.marketing,
    next_follow: r.feedback?.next_follow,
  };
}

export function marketingBody(v: FormValues) {
  return {
    potential: vs(v, 'potential'), dm_name: vs(v, 'dm_name'), dm_desig: vs(v, 'dm_desig'), dm_mobile: vs(v, 'dm_mobile'),
    dm_email: vs(v, 'dm_email'), competitor: vs(v, 'competitor'), exp_qty: numOrNull(vs(v, 'exp_qty')),
    decision_date: vs(v, 'decision_date') || null, stage: vs(v, 'stage'), remarks: vs(v, 'remarks'),
    next_action: vs(v, 'next_action'), next_follow: vs(v, 'next_follow') || null, person: vs(v, 'person'),
  };
}

/* ---------- follow-up ---------- */

export function followupFields(meta: Meta, userName: string): Field[] {
  return [
    { k: 'at', label: 'Follow-up date & time', t: 'datetime-local', req: true },
    { k: 'method', label: 'Method', t: 'select', o: meta.followup_methods, req: true },
    { k: 'person', label: 'Person contacted', req: true },
    { k: 'summary', label: 'Discussion summary', t: 'textarea', req: true },
    { k: 'next_action', label: 'Next action' },
    { k: 'next_date', label: 'Next follow-up date', t: 'date' },
    { k: '_by', label: 'Updated by', t: 'static', html: userName },
  ];
}

export const followupInitial = (r: RequestDetail) => ({ at: nowLocal(), person: r.marketing?.dm_name || r.school.contact });

export const followupCheck = (v: FormValues) =>
  vs(v, 'next_date') && vs(v, 'next_date') < vs(v, 'at').slice(0, 10) ? 'Next follow-up date must be after this follow-up.' : null;

export function followupBody(v: FormValues) {
  return { at: vs(v, 'at'), method: vs(v, 'method'), person: vs(v, 'person'), summary: vs(v, 'summary'), next_action: vs(v, 'next_action'), next_date: vs(v, 'next_date') || null };
}
