/*
 * Distributor ordering flows:
 *  - final order (directConfirm): POST /requests/<id>/dist-order with order + PO copy + pack
 *  - order for Myjo review (no directConfirm): POST /requests/<id>/dist-order
 *  - update own final order: PUT /requests/<id>/dist-order
 *  - "Create order" picker → existing school, or "+ New school" → POST /direct-orders (one form)
 */
import { useNavigate } from 'react-router-dom';
import { get, post, put, toApiError } from '../api';
import { useAuth } from '../auth';
import { nameOf, toId, today } from '../format';
import { useMeta } from '../meta';
import { requestPath } from '../nav';
import type { MyOrders, RequestDetail, WithMessage } from '../types';
import { fileIds, vs, type Field } from '../ui/Form';
import { useModal } from '../ui/Modal';
import { useToast } from '../ui/Toast';
import { finalOrderBody, finalOrderFields, needsPack, orderPrefill, orderProblem, packBody, packDefaults, packFields, packProblem, placeOrderBody, placeOrderCheck, placeOrderFields } from './orderForms';
import { distributorField, schoolBody, schoolFields } from './requestForms';

const FINAL_SUB = 'Your order is final; no Myjo approval is needed. Confirming finishes everything: the school is converted, its portal opens, and its academic support is set up.';

export function useDistOrders() {
  const modal = useModal();
  const meta = useMeta();
  const toast = useToast();
  const navigate = useNavigate();
  const { can, user } = useAuth();
  const direct = can('directConfirm');
  const isDist = user?.role === 'dist';

  const schoolStatic = (r: RequestDetail): Field => ({ k: '_school', label: 'School', t: 'static', html: `${r.school.name} · ${r.school.city}` });

  /** Final order (Create order / Confirm order). */
  const finalOrder = (r: RequestDetail, onSaved: () => void) => {
    const pack = needsPack(r);
    modal.form({
      title: 'Create order · ' + r.school.name,
      sub: FINAL_SUB,
      fields: [schoolStatic(r), ...finalOrderFields(meta, true), ...(pack ? packFields(meta) : [])],
      initial: { ...orderPrefill(r, r.dist_order), ...packDefaults() },
      submitLabel: 'Confirm order',
      validate: (v) => (pack && packProblem(v)) || orderProblem(v),
      onSubmit: async (v) => {
        const res = await post<WithMessage>(`/requests/${r.id}/dist-order`, { ...finalOrderBody(v), file_ids: fileIds(v, 'files'), ...(pack ? { pack: packBody(v) } : {}) });
        return res?.message || 'Order confirmed · school converted · academic support set up';
      },
      onSuccess: onSaved,
    });
  };

  /** Order sent to Myjo Marketing for review. */
  const placeOrder = (r: RequestDetail, onSaved: () => void) => {
    const again = !!r.dist_order;
    modal.form({
      title: (again ? 'Update and resubmit order · ' : 'Place book order · ') + r.school.name,
      sub: 'Myjo Marketing reviews the order. The school is marked Converted when Myjo confirms it.',
      fields: placeOrderFields(meta, `${r.school.name} · ${r.school.city}`),
      initial: orderPrefill(r, r.dist_order),
      submitLabel: again ? 'Resubmit order' : 'Place order',
      validate: placeOrderCheck,
      onSubmit: async (v) => {
        const res = await post<WithMessage>(`/requests/${r.id}/dist-order`, placeOrderBody(v));
        return res?.message || 'Order placed · Myjo Marketing will confirm';
      },
      onSuccess: onSaved,
    });
  };

  /** Distributor edits its own final order (order fields only). */
  const updateOrder = (r: RequestDetail, onSaved: () => void) =>
    modal.form({
      title: 'Update order · ' + r.school.name,
      sub: 'Changes are recorded in the audit trail and shared with Myjo.',
      fields: [schoolStatic(r), ...finalOrderFields(meta, false)],
      initial: { ...(r.order ?? orderPrefill(r, r.dist_order)), order_status: r.order_status ?? 'Order Confirmed' },
      submitLabel: 'Save order',
      validate: orderProblem,
      onSubmit: async (v) => {
        const res = await put<WithMessage>(`/requests/${r.id}/dist-order`, finalOrderBody(v));
        return res?.message || 'Order updated';
      },
      onSuccess: onSaved,
    });

  /** New school + order for Myjo review (distributors without directConfirm). */
  const newSchoolForReview = () =>
    modal.form({
      title: 'New school · book order',
      sub: 'The school is added and its order goes to Myjo Marketing. The school is marked Converted, and academic support is set up, when Myjo confirms it.',
      fields: [...schoolFields(meta, false), { sec: 'Book order' }, ...placeOrderFields(meta, '').filter((f) => !('k' in f) || f.k !== '_school')],
      initial: { ay: meta.academic_years[meta.academic_years.length - 1] ?? '' },
      submitLabel: 'Place order',
      validate: placeOrderCheck,
      onSubmit: async (v) => {
        const created = await post<RequestDetail & WithMessage>('/direct-orders', { school: schoolBody(v), ay: vs(v, 'ay'), order: placeOrderBody(v) });
        navigate(requestPath(created.id));
        return created.message || 'Order placed · Myjo Marketing will confirm';
      },
    });

  /** New school + final order + pack in one form. */
  const newSchoolOrder = () =>
    isDist && !direct ? newSchoolForReview() : modal.form({
      title: 'New school · order · academic support',
      sub: 'One form finishes everything: the school is added, the order is confirmed, the portal opens and academic support is set up. No Myjo approval is needed.',
      fields: [
        ...schoolFields(meta, false),
        ...(isDist ? [] : [{ sec: 'Distributor' } as Field, distributorField(meta, false, '')]),
        { sec: 'Book order' },
        ...finalOrderFields(meta, true),
        ...packFields(meta),
      ],
      initial: { ay: meta.academic_years[meta.academic_years.length - 1] ?? '', conf_date: today(), payment: 'Pending', order_status: 'Order Confirmed', ...packDefaults() },
      submitLabel: 'Confirm order',
      validate: (v) => packProblem(v) || orderProblem(v),
      onSubmit: async (v) => {
        // order_status and file_ids travel inside `order` for this endpoint.
        const created = await post<RequestDetail & WithMessage>('/direct-orders', {
          school: schoolBody(v),
          ay: vs(v, 'ay'),
          order: { ...finalOrderBody(v), file_ids: fileIds(v, 'files') },
          pack: packBody(v),
          ...(isDist ? {} : { distributor_id: toId(vs(v, 'distributor_id')) }),
        });
        navigate(requestPath(created.id));
        return created.message || 'Order confirmed · school converted · academic support set up';
      },
    });

  /** Entry point for a school that can be ordered for (request action `dist_order` / `dist_confirm`). */
  const orderFor = (r: RequestDetail, onSaved: () => void) => (direct ? finalOrder(r, onSaved) : placeOrder(r, onSaved));

  /** "Create order" button: pick one of my schools or add a new one. */
  const createOrder = async (onSaved: () => void) => {
    let data: MyOrders;
    try {
      data = await get<MyOrders>('/my-orders');
    } catch (e) {
      toast(toApiError(e).message, 'bad');
      return;
    }
    const mine = data.can_order ?? [];
    const options: [string, string][] = mine.map((c) => [String(c.id), `${nameOf(c.school)} · ${c.city} · ${c.status}`]);
    options.push(['__new', '+ New school (not in this list)']);
    let next: (() => void) | null = null;
    modal.form({
      title: 'Create order',
      sub: direct ? 'Your order is final and confirmed straight away; no Myjo approval is needed.' : 'Choose one of your schools, or add a new one. Myjo Marketing confirms the order.',
      fields: [
        {
          k: 'school', label: 'School', t: 'select', o: options, req: true,
          hint: mine.length ? 'Schools with a confirmed order are not listed' : 'You have no schools ready to order yet; add a new school',
        },
      ],
      initial: { school: !mine.length ? '__new' : '' },
      submitLabel: 'Next',
      onSubmit: async (v) => {
        const id = vs(v, 'school');
        if (id === '__new') {
          next = newSchoolOrder;
          return;
        }
        const r = await get<RequestDetail>(`/requests/${encodeURIComponent(id)}`);
        next = () => (r.actions.includes('dist_order') || r.actions.includes('dist_confirm') ? orderFor(r, onSaved) : toast('An order cannot be placed for this school right now.', 'bad'));
      },
      onSuccess: () => next?.(),
    });
  };

  return { finalOrder, placeOrder, updateOrder, orderFor, newSchoolOrder, createOrder };
}

