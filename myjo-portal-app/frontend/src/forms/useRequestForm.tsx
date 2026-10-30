/* Opens the demo-request form (new or edit). Used by Dashboard, Demo requests and Request detail. */
import { useNavigate } from 'react-router-dom';
import { post, put } from '../api';
import { useAuth } from '../auth';
import { useMeta } from '../meta';
import { requestPath } from '../nav';
import type { RequestDetail } from '../types';
import { useModal } from '../ui/Modal';
import { newRequestCheck, requestBody, requestFields, requestInitial } from './requestForms';

export function useRequestForm() {
  const modal = useModal();
  const meta = useMeta();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isDist = user?.role === 'dist';
  const ownLabel = [user?.org || user?.name, user?.phone].filter(Boolean).join(' · ');

  return (r: RequestDetail | null, onSaved?: () => void) =>
    modal.form({
      title: r ? 'Edit ' + r.no : 'New demo request',
      sub: r ? 'Changes are recorded in the audit trail.' : 'A Demo Request Number is generated when you submit.',
      fields: requestFields(meta, isDist, ownLabel),
      initial: requestInitial(r, meta),
      submitLabel: r ? 'Save changes' : 'Submit request',
      validate: r ? undefined : newRequestCheck,
      onSubmit: async (v) => {
        if (r) {
          await put(`/requests/${r.id}`, requestBody(v, isDist));
          onSaved?.();
          return 'Request updated';
        }
        const created = await post<RequestDetail>('/requests', requestBody(v, isDist));
        navigate(requestPath(created.id));
        return 'Submitted as ' + created.no;
      },
    });
}
