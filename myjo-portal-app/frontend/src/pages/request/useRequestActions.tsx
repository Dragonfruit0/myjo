/*
 * Handlers for every request action code. A button is rendered only when its code is in
 * `request.actions` (the server decides what the signed-in user may do right now).
 */
import { post, put, toApiError } from '../../api';
import { useAuth, useUser } from '../../auth';
import { CONF_ST, finalOrderBody, finalOrderFields, isConfirmed, needsPack, orderBody, orderPrefill, orderProblem, orderStatusCheck, orderStatusFields, orderStatusInitial, packBody, packDefaults, packFields, packProblem } from '../../forms/orderForms';
import { feedbackBody, feedbackCheck, feedbackFields, feedbackInitial, followupBody, followupCheck, followupFields, followupInitial, marketingBody, marketingFields, marketingInitial, scheduleBody, scheduleCheck, scheduleFields, scheduleInitial } from '../../forms/requestForms';
import { useDistOrders } from '../../forms/useDistOrders';
import { useRequestForm } from '../../forms/useRequestForm';
import { useMeta } from '../../meta';
import type { RequestAction, RequestDetail } from '../../types';
import { vs } from '../../ui/Form';
import { useModal } from '../../ui/Modal';
import { useToast } from '../../ui/Toast';
import { ShareDialog } from './ShareDialog';

export interface ActionButton {
  code: RequestAction;
  label: string;
  tone?: 'primary' | 'danger';
  run: () => void;
}

export function useRequestActions(r: RequestDetail, reload: () => void) {
  const modal = useModal();
  const meta = useMeta();
  const toast = useToast();
  const user = useUser();
  const { can } = useAuth();
  const openRequest = useRequestForm();
  const dist = useDistOrders();
  const base = `/requests/${r.id}`;

  /** POST with no input, then toast + reload. */
  const quick = (path: string, msg: string) => async () => {
    try {
      await post(base + path);
      toast(msg);
      reload();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };

  const reasonAction = (path: string, title: string, text: string, ok: string, msg: string, opts: { label?: string; key?: string; required?: boolean; danger?: boolean } = {}) => () =>
    modal.reason({
      title,
      text,
      label: opts.label,
      required: opts.required,
      ok,
      danger: opts.danger,
      onSubmit: async (reason) => {
        await post(base + path, { [opts.key ?? 'reason']: reason });
        return msg;
      },
      onSuccess: reload,
    });

  const schedule = () =>
    modal.form({
      title: (r.schedule ? 'Reschedule' : 'Schedule') + ' demo · ' + r.school.name,
      sub: 'Confirmation goes to the school, distributor, presenter and marketing person.',
      fields: scheduleFields(meta),
      initial: scheduleInitial(r),
      submitLabel: r.schedule ? 'Save new schedule' : 'Schedule demo',
      validate: scheduleCheck,
      onSubmit: async (v) => {
        await put(base + '/schedule', scheduleBody(v));
        return 'Demo scheduled · confirmation sent';
      },
      onSuccess: reload,
    });

  const share = () =>
    modal.open({
      title: 'Share demo details',
      render: (close) => <ShareDialog request={r} onClose={close} onShared={reload} />,
    });

  const feedback = () =>
    modal.form({
      title: 'Myjo demo feedback · ' + r.school.name,
      sub: 'Internal feedback. Saving marks the demo as completed.',
      fields: feedbackFields(meta),
      initial: feedbackInitial(r),
      submitLabel: 'Save feedback',
      validate: feedbackCheck,
      onSubmit: async (v) => {
        await put(base + '/feedback', feedbackBody(v));
        return 'Feedback saved · demo marked completed';
      },
      onSuccess: reload,
    });

  const marketing = () =>
    modal.form({
      title: 'Marketing feedback · ' + r.school.name,
      fields: marketingFields(meta),
      initial: marketingInitial(r),
      submitLabel: 'Save',
      onSubmit: async (v) => {
        await put(base + '/marketing', marketingBody(v));
        return 'Marketing feedback saved';
      },
      onSuccess: reload,
    });

  const followup = () =>
    modal.form({
      title: 'Log follow-up · ' + r.school.name,
      fields: followupFields(meta, user.name),
      initial: followupInitial(r),
      submitLabel: 'Add to history',
      validate: followupCheck,
      onSubmit: async (v) => {
        await post(base + '/followups', followupBody(v));
        return 'Follow-up logged';
      },
      onSuccess: reload,
    });

  const order = () => {
    const pack = needsPack(r);
    modal.form({
      title: 'Order status · ' + r.school.name,
      sub: 'A school is marked Converted only when the order is Confirmed or Partially Confirmed.',
      fields: orderStatusFields(meta, r, pack),
      initial: orderStatusInitial(r),
      submitLabel: 'Save order status',
      validate: (v) => orderStatusCheck(v, pack),
      onSubmit: async (v) => {
        const st = vs(v, 'order_status');
        const conf = isConfirmed(v);
        await put(base + '/order', conf ? { order_status: st, ...orderBody(v), ...(pack ? { pack: packBody(v) } : {}) } : { order_status: st });
        if (conf) return r.status === 'Converted' ? 'Order updated' : 'Order confirmed · school converted';
        return ['Not Interested', 'Lost to Competitor'].includes(st) ? 'Marked as not converted' : 'Order status saved';
      },
      onSuccess: reload,
    });
  };

  const acceptDist = () => {
    const pack = needsPack(r);
    const q = r.dist_order;
    modal.form({
      title: 'Accept & confirm order · ' + r.school.name,
      sub: 'Confirming converts the school and sets up its academic support.',
      fields: [
        { k: '_school', label: 'School', t: 'static', html: r.school.name },
        { k: '_dist', label: 'Distributor', t: 'static', html: r.distributor?.name },
        ...finalOrderFields(meta, false),
        ...(pack ? packFields(meta) : []),
      ],
      initial: { ...orderPrefill(r, q), remarks: 'Placed by distributor' + (q?.remarks ? ': ' + q.remarks : ''), ...packDefaults() },
      submitLabel: 'Confirm order',
      validate: (v) => orderProblem(v) || (pack ? packProblem(v) : null),
      onSubmit: async (v) => {
        await post(base + '/dist-order/accept', { ...finalOrderBody(v), ...(pack ? { pack: packBody(v) } : {}) });
        return 'Order confirmed · school converted';
      },
      onSuccess: reload,
    });
  };

  const assign = () =>
    modal.form({
      title: 'Assign ' + r.no,
      fields: [{ k: 'assigned_to', label: 'Myjo team member', t: 'select', o: meta.people.demo, req: true }],
      initial: { assigned_to: r.assigned_to ?? '' },
      submitLabel: 'Assign',
      onSubmit: async (v) => {
        await post(base + '/assign', { assigned_to: vs(v, 'assigned_to') });
        return 'Assigned to ' + vs(v, 'assigned_to');
      },
      onSuccess: reload,
    });

  const handlers: Record<RequestAction, () => void> = {
    edit: () => openRequest(r, reload),
    review: quick('/review', 'Moved to Under Review'),
    approve: reasonAction('/approve', 'Approve ' + r.no, r.school.name + ' · school and distributor are notified.', 'Approve', 'Approved · notifications sent', { label: 'Remarks (optional)', key: 'note', required: false }),
    reject: reasonAction('/reject', 'Reject ' + r.no, 'The school and distributor are told the reason.', 'Reject request', 'Rejected · notifications sent', { danger: true }),
    info: reasonAction('/info', 'Request more information', 'Sent to the distributor and school contact. The request stays Under Review.', 'Send request', 'Information request sent', { label: 'What do you need?' }),
    hold: reasonAction('/hold', 'Put ' + r.no + ' on hold', 'School and distributor are notified.', 'Put on hold', 'On hold'),
    resume: quick('/resume', 'Back to Under Review'),
    assign,
    schedule,
    share,
    feedback,
    marketing,
    followup,
    order,
    dist_order: () => dist.orderFor(r, reload),
    dist_confirm: () => dist.finalOrder(r, reload),
    dist_update: () => dist.updateOrder(r, reload),
    accept_dist: acceptDist,
    return_dist: reasonAction('/dist-order/return', 'Return order for changes', r.school.name + ' · the distributor can update and resubmit.', 'Return to distributor', 'Returned to distributor', { label: 'What needs to change?' }),
    reject_dist: reasonAction('/dist-order/reject', 'Reject distributor order', r.school.name + ' · the distributor is told the reason.', 'Reject order', 'Order rejected', { danger: true }),
    cancel: reasonAction('/cancel', 'Request cancellation · ' + r.no, 'Records are never deleted. Admin must approve before the record is cancelled.', 'Send for approval', 'Sent to Admin for approval', { danger: true }),
  };

  const has = (c: RequestAction) => r.actions.includes(c);
  const btn = (code: RequestAction, label: string, tone?: 'primary' | 'danger'): ActionButton | null => (has(code) ? { code, label, tone, run: handlers[code] } : null);
  const converted = r.status === 'Converted';

  /** Buttons for the action bar under the title (card-specific ones are rendered in their cards). */
  const top = [
    btn('edit', 'Edit request'),
    btn('review', 'Start review'),
    btn('approve', 'Approve', 'primary'),
    btn('info', 'Request more info'),
    btn('reject', 'Reject', 'danger'),
    btn('hold', 'Put on hold'),
    btn('resume', 'Resume review'),
    btn('assign', 'Assign'),
    r.schedule ? null : btn('schedule', 'Schedule demo', 'primary'),
    r.feedback ? null : btn('feedback', 'Enter demo feedback', 'primary'),
    btn('followup', 'Log follow-up'),
    btn('marketing', 'Marketing feedback'),
    btn('order', 'Update order status', converted || r.dist_order?.status === 'Submitted' ? undefined : 'primary'),
    btn('dist_order', can('directConfirm') ? 'Create order' : r.dist_order ? 'Update & resubmit order' : 'Place order', 'primary'),
    btn('dist_confirm', 'Confirm order', 'primary'),
    btn('dist_update', 'Update order'),
    btn('cancel', 'Request cancellation', 'danger'),
  ].filter((b): b is ActionButton => !!b);

  return { top, handlers, has, confirmed: CONF_ST.includes(r.order_status ?? '') };
}

export function ActionButtons({ buttons, size }: { buttons: ActionButton[]; size?: 'sm' }) {
  return (
    <>
      {buttons.map((b) => (
        <button key={b.code + b.label} type="button" className={['btn', b.tone, size].filter(Boolean).join(' ')} onClick={b.run}>
          {b.label}
        </button>
      ))}
    </>
  );
}
