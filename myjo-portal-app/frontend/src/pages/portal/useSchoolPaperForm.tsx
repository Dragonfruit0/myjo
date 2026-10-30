/* School › "Request question paper" (POST /portal/papers). Series options come from the school's order. */
import { get, post, toApiError } from '../../api';
import { numOrNull, today } from '../../format';
import { useMeta } from '../../meta';
import type { PortalOverview } from '../../types';
import { vs } from '../../ui/Form';
import { useModal } from '../../ui/Modal';
import { useToast } from '../../ui/Toast';

export function useSchoolPaperForm() {
  const modal = useModal();
  const meta = useMeta();
  const toast = useToast();

  return async (onSaved?: () => void, overview?: PortalOverview) => {
    let ov = overview;
    if (!ov) {
      try {
        ov = await get<PortalOverview>('/portal/overview');
      } catch (e) {
        toast(toApiError(e).message, 'bad');
        return;
      }
    }
    const series = ov.order.series.length ? ov.order.series : meta.series.map((s) => s.name);
    modal.form({
      title: 'Request a question paper',
      sub: ov.school.name,
      fields: [
        { k: 'ay', label: 'Academic year', t: 'select', o: meta.academic_years, req: true },
        { k: 'series', label: 'Book series', t: 'select', o: series, req: true },
        { k: 'cls', label: 'Class', t: 'select', o: meta.classes, req: true },
        { k: 'subject', label: 'Subject', t: 'select', o: meta.subjects, req: true },
        { k: 'exam', label: 'Exam type', t: 'select', o: meta.exam_types, req: true },
        { k: 'due_date', label: 'Required delivery date', t: 'date', req: true },
        { k: 'max_marks', label: 'Maximum marks', t: 'number', req: true },
        { k: 'remarks', label: 'Chapters, pattern or other remarks', t: 'textarea' },
      ],
      initial: { ay: ov.order.ay, series: series[0] ?? '' },
      submitLabel: 'Submit request',
      validate: (v) => (vs(v, 'due_date') < today() ? 'Required date cannot be in the past.' : null),
      onSubmit: async (v) => {
        const created = await post<{ no?: string }>('/portal/papers', {
          ay: vs(v, 'ay'), series: vs(v, 'series'), cls: vs(v, 'cls'), subject: vs(v, 'subject'), exam: vs(v, 'exam'),
          due_date: vs(v, 'due_date'), max_marks: numOrNull(vs(v, 'max_marks')), remarks: vs(v, 'remarks'),
        });
        return created?.no ? `Request ${created.no} submitted` : 'Request submitted';
      },
      onSuccess: onSaved,
    });
  };
}
