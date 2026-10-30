/* Client-side copies of the server's password/PIN rules (API.md › Auth). The server stays the authority. */

export function pwProblem(p: string): string | null {
  if (p.length < 8) return 'Password must be at least 8 characters.';
  if (!/[A-Za-z]/.test(p) || !/\d/.test(p)) return 'Password must include letters and numbers.';
  return null;
}

export function pinProblem(p: string): string | null {
  if (!/^\d{4}$/.test(p)) return 'PIN must be exactly 4 digits.';
  if (/^(\d)\1{3}$/.test(p) || ['1234', '4321', '0123', '9876'].includes(p)) return 'Choose a PIN that is harder to guess.';
  return null;
}
