/*
 * Training session, question paper and resource forms. Each hook loads the lists it needs
 * (ordered schools, resources) when the form is opened, so any screen can offer the button.
 */
import { useNavigate } from 'react-router-dom';
import { asList, get, post, put, toApiError } from '../api';
import { useUser } from '../auth';
import { fd, nameOf, nowLocal, numOrNull, toId, today } from '../format';
import { useMeta } from '../meta';
import { trainingPath } from '../nav';
import type { Id, ListResponse, OrderedSchool, Paper, Resource, TrainingDetail } from '../types';
import { firstFileId, va, vs, type Field, type FormValues } from '../ui/Form';
import { useModal } from '../ui/Modal';
import { useToast } from '../ui/Toast';

type Many<T> = T[] | ListResponse<T>;

export async function loadOrderedSchools(): Promise<OrderedSchool[]> {
  return asList(await get<Many<OrderedSchool>>('/ordered-schools'));
}

const schoolOption = (s: OrderedSchool): [string, string] => [
  String(s.request_id),
  `${nameOf(s.school)} · ${s.city}${s.order?.status && s.order.status !== 'Confirmed' ? ' · distributor order, awaiting Myjo' : ''}`,
];

const sid = (id: Id) => String(id);

/* ---------- teacher training ---------- */

export function useTrainingForm() {
  const modal = useModal();
  const meta = useMeta();
  const toast = useToast();
  const navigate = useNavigate();

  return async ({ existing, preselect, onSaved }: { existing?: TrainingDetail; preselect?: Id; onSaved?: () => void }) => {
    let schools: OrderedSchool[];
    let resources: Resource[];
    try {
      [schools, resources] = await Promise.all([loadOrderedSchools(), get<Many<Resource>>('/resources').then(asList)]);
    } catch (e) {
      toast(toApiError(e).message, 'bad');
      return;
    }
    const opts: [string, string][] = schools.map(schoolOption);
    for (const s of existing?.schools ?? []) if (!opts.some((o) => o[0] === sid(s.request_id))) opts.push([sid(s.request_id), `${s.name} · ${s.city}`]);
    const nameFor = (id: string) => opts.find((o) => o[0] === id)?.[1].split(' · ')[0] ?? id;
    const online = (v: FormValues) => vs(v, 'mode') === 'Online';

    const fields: Field[] = [
      { sec: 'Session' },
      { k: 'title', label: 'Training title', req: true, wide: true, ph: 'e.g. Term 2 orientation: Maths Pathways' },
      { k: 'type', label: 'Training type', t: 'select', o: meta.training_types, req: true },
      { k: 'ay', label: 'Academic year', t: 'select', o: meta.academic_years, req: true },
      { k: 'series', label: 'Book series', t: 'multi', o: meta.series.map((s) => s.name), req: true },
      { k: 'classes', label: 'Classes covered', t: 'multi', o: meta.classes, req: true },
      { k: 'subjects', label: 'Subjects covered', t: 'multi', o: meta.subjects, req: true },
      { sec: 'Schedule' },
      { k: 'at', label: 'Training date & time', t: 'datetime-local', req: true },
      { k: 'mode', label: 'Training mode', t: 'select', o: ['Online', 'Offline'], req: true },
      { k: 'trainer', label: 'Trainer assigned', t: 'select', o: meta.people.acad, req: true },
      { k: 'link', label: 'Online meeting link', t: 'url', ph: 'https://', hint: 'Required for online sessions', when: online },
      { k: 'venue', label: 'Offline venue', t: 'textarea', rows: 2, hint: 'Required for offline sessions', when: (v) => !online(v) },
      { k: 'agenda', label: 'Training agenda', t: 'textarea', req: true },
      { sec: 'Schools', hint: 'Pick one or more ordered schools. The same session is shared with every selected school. Enter expected teachers for each selected school.' },
      { k: 'school_ids', label: 'Select school(s)', t: 'multi', o: opts, req: true },
      ...opts.map(([id, label]): Field => ({ k: 'exp_' + id, label: 'Expected teachers · ' + label.split(' · ')[0], t: 'number', when: (v) => va(v, 'school_ids').includes(id) })),
      { sec: 'Resources & notes' },
      {
        k: 'resource_ids', label: 'Related manuals & resources', t: 'multi',
        o: resources.filter((x) => x.status !== 'Cancelled' && x.status !== 'Archived').map((x) => [sid(x.id), x.title + (x.status === 'Draft' ? ' (draft)' : '')] as const),
        hint: 'A school sees a resource only once it is published and available to that school.',
      },
      { k: 'remarks', label: 'Remarks', t: 'textarea', rows: 2 },
      { k: 'instructions', label: 'Special instructions', t: 'textarea', rows: 2 },
      { k: 'status', label: 'Save as', t: 'select', o: ['Draft', 'Scheduled'], req: true, hint: 'Scheduled shares the session with the selected schools and notifies them. Drafts are not visible to schools.' },
    ];

    let initial: Record<string, unknown>;
    if (existing) {
      initial = { ...existing, school_ids: existing.schools.map((s) => sid(s.request_id)), resource_ids: existing.resources.map((x) => sid(x.id)) };
      for (const s of existing.schools) initial['exp_' + sid(s.request_id)] = s.expected;
    } else {
      const pre = schools.find((s) => preselect !== undefined && sid(s.request_id) === sid(preselect));
      initial = {
        mode: 'Online', status: 'Draft', school_ids: pre ? [sid(pre.request_id)] : [],
        series: pre?.order.series ?? [], classes: pre?.order.classes ?? [], subjects: pre?.order.subjects ?? [], ay: meta.academic_years[0] ?? '',
      };
    }

    const validate = (v: FormValues): string | null => {
      if (online(v) && !vs(v, 'link')) return 'Enter the online meeting link.';
      if (!online(v) && !vs(v, 'venue')) return 'Enter the offline venue.';
      const changed = !existing || existing.at.slice(0, 16) !== vs(v, 'at') || existing.status !== 'Scheduled';
      if (vs(v, 'status') === 'Scheduled' && vs(v, 'at') < nowLocal() && changed) return 'Training date & time must be in the future to schedule the session.';
      for (const id of va(v, 'school_ids')) if (!(Number(vs(v, 'exp_' + id)) > 0)) return 'Enter expected teachers for ' + nameFor(id) + '.';
      return null;
    };

    modal.form({
      title: existing ? 'Edit ' + existing.no : 'New group training session',
      sub: existing ? existing.title : 'One session for one or more schools.',
      fields,
      initial,
      submitLabel: existing ? 'Save changes' : 'Save session',
      validate,
      fieldAliases: { schools: 'school_ids' },
      onSubmit: async (v) => {
        const body = {
          title: vs(v, 'title'), type: vs(v, 'type'), ay: vs(v, 'ay'), series: va(v, 'series'), classes: va(v, 'classes'), subjects: va(v, 'subjects'),
          at: vs(v, 'at'), mode: vs(v, 'mode'), trainer: vs(v, 'trainer'),
          link: online(v) ? vs(v, 'link') : '', venue: online(v) ? '' : vs(v, 'venue'), agenda: vs(v, 'agenda'),
          schools: va(v, 'school_ids').map((id) => ({ request_id: toId(id), expected: Number(vs(v, 'exp_' + id)) })),
          resource_ids: va(v, 'resource_ids').map(toId), remarks: vs(v, 'remarks'), instructions: vs(v, 'instructions'), status: vs(v, 'status'),
        };
        if (existing) {
          await put(`/trainings/${existing.id}`, body);
          onSaved?.();
          return 'Session updated';
        }
        const created = await post<TrainingDetail>('/trainings', body);
        onSaved?.();
        if (created?.id !== undefined) navigate(trainingPath(created.id));
        return body.status === 'Scheduled' ? 'Session scheduled · schools notified' : 'Draft saved';
      },
    });
  };
}

/* ---------- question papers ---------- */

export function usePaperForm() {
  const modal = useModal();
  const meta = useMeta();
  const toast = useToast();

  return async ({ existing, preselect, onSaved }: { existing?: Paper; preselect?: Id; onSaved?: () => void }) => {
    let schools: OrderedSchool[];
    try {
      schools = await loadOrderedSchools();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
      return;
    }
    const opts = schools.map(schoolOption);
    if (existing && !opts.some((o) => o[0] === sid(existing.request_id))) opts.push([sid(existing.request_id), nameOf(existing.school)]);
    const fields: Field[] = [
      { k: 'request_id', label: 'School', t: 'select', o: opts, req: true },
      { k: 'ay', label: 'Academic year', t: 'select', o: meta.academic_years, req: true },
      { k: 'cls', label: 'Class', t: 'select', o: meta.classes, req: true },
      { k: 'subject', label: 'Subject', t: 'select', o: meta.subjects, req: true },
      { k: 'series', label: 'Book series', t: 'select', o: meta.series.map((s) => s.name), req: true },
      { k: 'exam', label: 'Exam type', t: 'select', o: meta.exam_types, req: true },
      { k: 'due_date', label: 'Required delivery date', t: 'date', req: true },
      { k: 'assignee', label: 'Assigned academic team member', t: 'select', o: meta.people.acad },
      { k: 'max_marks', label: 'Maximum marks', t: 'number' },
      { k: 'delivery_date', label: 'Delivery date', t: 'date' },
      { k: 'status', label: 'Status', t: 'select', o: meta.paper_statuses, req: true, hint: 'Only Published papers become downloadable for the school.' },
      { k: 'qp_file', label: 'Question paper file', t: 'file', accept: '.pdf,.doc,.docx' },
      { k: 'ak_file', label: 'Answer key file', t: 'file', accept: '.pdf,.doc,.docx' },
      { k: 'remarks', label: 'Remarks', t: 'textarea', rows: 2 },
    ];
    const pre = schools.find((s) => preselect !== undefined && sid(s.request_id) === sid(preselect));
    const initial: Record<string, unknown> = existing
      ? { ...existing, request_id: sid(existing.request_id) }
      : { request_id: pre ? sid(pre.request_id) : '', status: 'New', ay: meta.academic_years[0] ?? '', series: pre?.order.series[0] ?? '' };
    const live = ['Published', 'Delivered'];
    modal.form({
      title: existing ? `Edit ${existing.no} · ${nameOf(existing.school)}` : 'New question paper',
      fields,
      initial,
      submitLabel: existing ? 'Save' : 'Create',
      fieldAliases: { qp_file_id: 'qp_file', ak_file_id: 'ak_file' },
      validate: (v) => {
        if (vs(v, 'status') !== 'New' && !vs(v, 'assignee')) return 'Assign an academic team member first.';
        if (live.includes(vs(v, 'status')) && !firstFileId(v, 'qp_file')) return 'Upload the question paper file before publishing.';
        if (vs(v, 'status') === 'Delivered' && !vs(v, 'delivery_date')) return 'Enter the delivery date.';
        return null;
      },
      onSubmit: async (v) => {
        const body = {
          request_id: toId(vs(v, 'request_id')), ay: vs(v, 'ay'), cls: vs(v, 'cls'), subject: vs(v, 'subject'), series: vs(v, 'series'),
          exam: vs(v, 'exam'), due_date: vs(v, 'due_date'), assignee: vs(v, 'assignee'), max_marks: numOrNull(vs(v, 'max_marks')),
          delivery_date: vs(v, 'delivery_date') || null, status: vs(v, 'status'),
          qp_file_id: firstFileId(v, 'qp_file'), ak_file_id: firstFileId(v, 'ak_file'), remarks: vs(v, 'remarks'),
        };
        if (existing) await put(`/papers/${existing.id}`, body);
        else await post('/papers', body);
        onSaved?.();
        return existing ? 'Question paper updated' : 'Question paper created';
      },
    });
  };
}

/* ---------- manuals & resources ---------- */

export const ACCESS_ALL = 'All Ordered Schools';
export const ACCESS_SELECTED = 'Selected Schools Only';

export function useResourceForm() {
  const modal = useModal();
  const meta = useMeta();
  const toast = useToast();
  const user = useUser();

  return async ({ existing, preselect, onSaved }: { existing?: Resource; preselect?: Id; onSaved?: () => void }) => {
    let schools: OrderedSchool[];
    try {
      schools = await loadOrderedSchools();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
      return;
    }
    const selected = (v: FormValues) => vs(v, 'access') === ACCESS_SELECTED;
    const fields: Field[] = [
      { k: 'title', label: 'Resource title', req: true, wide: true },
      { k: 'type', label: 'Resource type', t: 'select', o: meta.resource_types, req: true },
      { k: 'series', label: 'Book series', t: 'select', o: meta.series.map((s) => s.name), req: true },
      { k: 'cls', label: 'Class', t: 'select', o: ['All classes', ...meta.classes], req: true },
      { k: 'subject', label: 'Subject', t: 'select', o: meta.subjects, req: true },
      { k: 'ay', label: 'Academic year', t: 'select', o: meta.academic_years, req: true },
      { k: 'version', label: 'Version number', req: true, ph: 'e.g. 1.0' },
      { k: 'description', label: 'Description', t: 'textarea' },
      { k: 'file', label: 'File upload (PDF, Word, PowerPoint, Excel or ZIP)', t: 'file', accept: '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip', wide: true },
      { k: 'link', label: 'Video link (for training videos)', t: 'url', wide: true, ph: 'https://' },
      { k: 'access', label: 'Access level', t: 'select', o: [ACCESS_ALL, ACCESS_SELECTED], req: true },
      { k: 'status', label: 'Status', t: 'select', o: existing?.status === 'Archived' ? ['Draft', 'Published', 'Archived'] : ['Draft', 'Published'], req: true, hint: 'Only Published resources are visible to schools.' },
      { k: 'school_ids', label: 'Selected schools', t: 'multi', o: schools.map(schoolOption), when: selected },
      { k: '_by', label: 'Uploaded by', t: 'static', html: `${existing?.uploaded_by ?? user.name} · ${fd(existing?.upload_date ?? today())}` },
    ];
    const pre = schools.find((s) => preselect !== undefined && sid(s.request_id) === sid(preselect));
    const initial: Record<string, unknown> = existing
      ? { ...existing, school_ids: (existing.school_ids ?? []).map(sid) }
      : {
          status: 'Draft', access: pre ? ACCESS_SELECTED : ACCESS_ALL, ay: meta.academic_years[0] ?? '', version: '1.0', cls: 'All classes',
          school_ids: pre ? [sid(pre.request_id)] : [], series: pre?.order.series[0] ?? '',
        };
    modal.form({
      title: existing ? 'Edit ' + existing.no : 'Upload academic resource',
      fields,
      initial,
      submitLabel: existing ? 'Save' : 'Save resource',
      fieldAliases: { file_id: 'file' },
      validate: (v) => {
        if (!firstFileId(v, 'file') && !vs(v, 'link')) return 'Upload a file or add a video link.';
        if (selected(v) && !va(v, 'school_ids').length) return 'Choose at least one school, or set access to All Ordered Schools.';
        return null;
      },
      onSubmit: async (v) => {
        const body = {
          title: vs(v, 'title'), type: vs(v, 'type'), series: vs(v, 'series'), cls: vs(v, 'cls'), subject: vs(v, 'subject'), ay: vs(v, 'ay'),
          description: vs(v, 'description'), file_id: firstFileId(v, 'file'), link: vs(v, 'link'), version: vs(v, 'version'),
          access: vs(v, 'access'), school_ids: selected(v) ? va(v, 'school_ids').map(toId) : [], status: vs(v, 'status'),
        };
        if (existing) await put(`/resources/${existing.id}`, body);
        else await post('/resources', body);
        onSaved?.();
        return existing ? 'Resource updated' : 'Resource saved';
      },
    });
  };
}
