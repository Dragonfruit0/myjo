/* "My account" modal: change password and/or PIN (POST /auth/change). */
import { post } from '../api';
import { useAuth } from '../auth';
import { vs } from '../ui/Form';
import { useModal } from '../ui/Modal';
import { pinProblem, pwProblem } from './passwordRules';

export function useMyAccount() {
  const modal = useModal();
  const { user } = useAuth();
  return () =>
    modal.form({
      title: 'My account',
      sub: `${user?.name ?? ''} · username ${user?.username ?? ''}`,
      fields: [
        { k: 'current_password', label: 'Current password', t: 'password', req: true, autoComplete: 'current-password' },
        { sec: 'Change password', hint: 'Leave blank to keep your password' },
        { k: 'new_password', label: 'New password', t: 'password' },
        { k: 'confirm_password', label: 'Confirm new password', t: 'password' },
        { sec: 'Change PIN', hint: 'Leave blank to keep your PIN' },
        { k: 'new_pin', label: 'New 4-digit PIN', t: 'password', pin: true },
        { k: 'confirm_pin', label: 'Confirm new PIN', t: 'password', pin: true },
      ],
      submitLabel: 'Save changes',
      validate: (v) => {
        const p1 = vs(v, 'new_password');
        const n1 = vs(v, 'new_pin');
        if (!p1 && !n1) return 'Enter a new password or a new PIN.';
        if (p1) {
          const e = pwProblem(p1);
          if (e) return e;
          if (p1 !== vs(v, 'confirm_password')) return 'The two new passwords do not match.';
        }
        if (n1) {
          const e = pinProblem(n1);
          if (e) return e;
          if (n1 !== vs(v, 'confirm_pin')) return 'The two new PINs do not match.';
        }
        return null;
      },
      onSubmit: async (v) => {
        const p1 = vs(v, 'new_password');
        const n1 = vs(v, 'new_pin');
        await post('/auth/change', { current_password: v.current_password, ...(p1 ? { new_password: p1 } : {}), ...(n1 ? { new_pin: n1 } : {}) });
        return (p1 && n1 ? 'Password and PIN' : p1 ? 'Password' : 'PIN') + ' updated';
      },
    });
}
