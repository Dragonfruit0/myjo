/* Menu groups, labels and order (same as the prototype NAV) plus screen → route mapping. */
import type { Id, Role, ScreenCode, ScreenLink } from './types';

export const NAV: { group: string; items: [ScreenCode, string][] }[] = [
  {
    group: 'Pipeline',
    items: [
      ['dashboard', 'Dashboard'],
      ['requests', 'Demo requests'],
      ['marketing', 'Marketing & follow-ups'],
      ['orders', 'Book orders'],
      ['myorders', 'My orders'],
    ],
  },
  {
    group: 'Academic support',
    items: [
      ['acschools', 'Ordered schools'],
      ['training', 'Teacher training'],
      ['papers', 'Question papers'],
      ['resources', 'Manuals & resources'],
      ['downloads', 'Downloads'],
    ],
  },
  { group: 'Insights', items: [['reports', 'Reports']] },
  {
    group: 'Control',
    items: [
      ['notifications', 'Notifications'],
      ['audit', 'Audit trail'],
      ['users', 'Users & roles'],
      ['masters', 'Subjects & series'],
      ['access', 'Access control'],
    ],
  },
  {
    group: 'My school',
    items: [
      ['portal', 'Overview'],
      ['mytraining', 'Teacher training'],
      ['library', 'Library & downloads'],
      ['support', 'Support requests'],
      ['history', 'Download history'],
    ],
  },
];

export const SCREEN_PATH: Record<ScreenCode, string> = {
  dashboard: '/dashboard',
  requests: '/requests',
  marketing: '/marketing',
  orders: '/orders',
  myorders: '/my-orders',
  acschools: '/ordered-schools',
  training: '/training',
  papers: '/papers',
  resources: '/resources',
  downloads: '/downloads',
  reports: '/reports',
  notifications: '/notifications',
  audit: '/audit',
  users: '/users',
  masters: '/masters',
  access: '/access',
  portal: '/portal',
  mytraining: '/portal/training',
  library: '/portal/library',
  support: '/portal/support',
  history: '/portal/history',
};

export const requestPath = (id: Id) => `/requests/${encodeURIComponent(String(id))}`;
export const trainingPath = (id: Id) => `/training/${encodeURIComponent(String(id))}`;

/** Turns a dashboard/KPI link (`"requests"` or `{screen,id}`) into a route. */
export function linkPath(link: string | ScreenLink | null | undefined): string {
  if (!link) return '/';
  const screen = typeof link === 'string' ? link : link.screen;
  const id = typeof link === 'string' ? undefined : link.id;
  if (id !== undefined && id !== null) {
    if (screen === 'requests' || screen === 'req' || screen === 'request') return requestPath(id);
    if (screen === 'training' || screen === 'trs' || screen === 'trainings') return trainingPath(id);
  }
  if (screen === 'req') return SCREEN_PATH.requests;
  if (screen === 'trs') return SCREEN_PATH.training;
  return SCREEN_PATH[screen as ScreenCode] ?? '/';
}

export function homePath(role: Role, screens: ScreenCode[]): string {
  if (role === 'school') return SCREEN_PATH[screens.includes('portal') ? 'portal' : screens[0] ?? 'portal'];
  if (screens.includes('dashboard')) return SCREEN_PATH.dashboard;
  return screens.length ? SCREEN_PATH[screens[0]] : SCREEN_PATH.dashboard;
}

export const ROLES: Role[] = ['admin', 'mgmt', 'demo', 'mkt', 'acad', 'dist', 'school'];

export const ROLE_LABEL: Record<Role, string> = {
  admin: 'Admin',
  mgmt: 'Management',
  demo: 'Myjo Demo Team',
  mkt: 'Marketing Team',
  acad: 'Academic Support Team',
  dist: 'Distributor',
  school: 'School User',
};

export const ROLE_DESC: Record<Role, string> = {
  admin: 'Users, access control, approvals and all data',
  mgmt: 'Dashboards, reports, conversion and team performance',
  demo: 'Review requests, schedule demos, share links, demo feedback',
  mkt: 'Follow-ups, quotations, order status and conversion',
  acad: 'Group training, question papers, manuals and resources',
  dist: 'Submit demo requests and track your schools',
  school: 'Your school’s training, question papers and resources',
};

export const ROLE_SLUG: Record<Role, string> = {
  admin: 'admin',
  mgmt: 'management',
  demo: 'demo-team',
  mkt: 'marketing',
  acad: 'academic',
  dist: 'distributor',
  school: 'school',
};

export const ROLE_DOT: Record<Role, string> = {
  admin: 'var(--accent)',
  mgmt: 'var(--b-purple)',
  demo: 'var(--b-blue)',
  mkt: 'var(--b-orange)',
  acad: 'var(--b-green)',
  dist: 'var(--b-brown)',
  school: 'var(--b-pink)',
};
