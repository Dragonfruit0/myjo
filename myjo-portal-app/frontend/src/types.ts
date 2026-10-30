/*
 * Types for the Myjo Portal API v1, verified against the Flask code (backend/app/api) and
 * real responses. Field names mirror the API exactly (snake_case).
 * Cancelled papers, trainings and resources are reported with `status: "Cancelled"`.
 */

export type Id = number | string;

export type Role = 'admin' | 'mgmt' | 'demo' | 'mkt' | 'acad' | 'dist' | 'school';

export type ScreenCode =
  | 'dashboard' | 'requests' | 'marketing' | 'orders' | 'myorders' | 'acschools' | 'training'
  | 'papers' | 'resources' | 'downloads' | 'reports' | 'notifications' | 'audit' | 'users'
  | 'masters' | 'access' | 'portal' | 'mytraining' | 'library' | 'support' | 'history';

export type PermCode =
  | 'createRequest' | 'editRequest' | 'placeOrder' | 'directConfirm' | 'review' | 'schedule'
  | 'feedback' | 'marketing' | 'order' | 'academic' | 'publish' | 'revoke' | 'approveCancel'
  | 'seeInternal';

export interface ListResponse<T> {
  items: T[];
  total?: number;
}

/** Most write endpoints that return a record also include a ready-made toast message. */
export interface WithMessage {
  message?: string;
}

/* ---------- auth ---------- */

export interface User {
  id: Id;
  username: string;
  name: string;
  email: string;
  phone: string;
  role: Role;
  role_label: string;
  org: string | null;
  /** the school's demo-request id (school users only) */
  school_id: Id | null;
  school_name: string | null;
}

export interface LoginResponse {
  token: string;
  user: User;
  must_change: boolean;
}

export interface MeResponse {
  user: User;
  screens: ScreenCode[];
  perms: PermCode[];
}

/* ---------- files ---------- */

export interface FileRef {
  id: Id;
  name: string;
  size?: number;
  mime?: string;
}

/* ---------- meta ---------- */

export interface SeriesMeta {
  name: string;
  color: string;
}

export interface DistributorMeta {
  id: Id;
  name: string;
  phone: string;
}

export interface Meta {
  classes: string[];
  subjects: string[];
  series: SeriesMeta[];
  all_series_colors: Record<string, string>;
  academic_years: string[];
  boards: string[];
  request_statuses: string[];
  order_statuses: string[];
  confirmed_statuses: string[];
  training_statuses: string[];
  paper_statuses: string[];
  resource_statuses: string[];
  exam_types: string[];
  resource_types: string[];
  training_types: string[];
  followup_methods: string[];
  payment_statuses: string[];
  discussion_stages: string[];
  requested_items: string[];
  interest_levels: string[];
  access_levels: string[];
  people: { demo: string[]; mkt: string[]; acad: string[] };
  distributors: DistributorMeta[];
  role_labels: Record<string, string>;
}

/* ---------- dashboard & search ---------- */

/** `screen` uses screen codes plus "req" (request detail) and "trs" (training detail); `id` may be null. */
export interface ScreenLink {
  screen: string;
  id?: Id | null;
}

export interface DashKpi {
  group: string;
  label: string;
  value: number | string;
  link: string | ScreenLink;
  tone?: string | null;
}

export interface DashItem {
  date: string;
  title: string;
  subtitle: string;
  link: ScreenLink;
  late?: boolean;
}

export interface DownloadsBySchool {
  request_id: Id;
  school: string;
  papers: number;
  resources: number;
  last: string | null;
}

export interface PendingCancellation {
  entity: 'request' | 'training' | 'paper' | 'resource';
  id: Id;
  ref: string;
  label: string;
  name: string;
  reason: string;
  by: string;
  at: string;
}

export interface Dashboard {
  kpis: DashKpi[];
  overdue: DashItem[];
  upcoming: DashItem[];
  my_work: { title: string; items: DashItem[] }[];
  downloads_by_school: DownloadsBySchool[];
  funnel: { label: string; value: number }[];
  no_download_schools: string[];
  pending_cancellations: PendingCancellation[];
}

export interface SearchResults {
  requests: RequestListItem[];
  trainings: { id: Id; no: string; title: string; status: string; schools: string }[];
  papers: { id: Id; no: string; school: string; cls: string; subject: string; status: string }[];
  resources: { id: Id; no: string; title: string; type: string; series: string; status: string }[];
}

/* ---------- demo requests ---------- */

export interface SchoolInfo {
  id?: Id;
  name: string;
  city: string;
  state: string;
  board: string;
  /* detail only */
  address?: string;
  pincode?: string;
  strength?: number | null;
  contact?: string;
  designation?: string;
  mobile?: string;
  email?: string;
}

export interface Party {
  id: Id;
  name: string;
  phone?: string;
}

export interface RequestListItem {
  id: Id;
  no: string;
  created_at: string;
  ay: string;
  status: string;
  order_status: string | null;
  school: SchoolInfo;
  distributor: Party;
  assigned_to: string | null;
  pref_date: string | null;
  pref_time: string | null;
  cancelled: boolean;
  cancel_pending: boolean;
  direct: boolean;
}

export type RequestAction =
  | 'edit' | 'review' | 'approve' | 'reject' | 'info' | 'hold' | 'resume' | 'assign' | 'schedule'
  | 'share' | 'feedback' | 'marketing' | 'followup' | 'order' | 'dist_order' | 'dist_update'
  | 'dist_confirm' | 'accept_dist' | 'return_dist' | 'reject_dist' | 'cancel';

export interface Note {
  at: string;
  by: string;
  type: string;
  text: string;
}

export interface Schedule {
  at: string;
  mode: 'Online' | 'Offline';
  presenter: string;
  marketing: string;
  platform: string | null;
  link: string | null;
  venue: string | null;
  agenda: string | null;
  instructions: string | null;
  shared_at: string | null;
  reminded: boolean;
}

export interface Feedback {
  by: string;
  date: string;
  attendees: string;
  designations: string | null;
  classes: string[];
  subjects: string[];
  series: string[];
  interest: string;
  requirements: string | null;
  requested: string[];
  objections: string | null;
  competitor: string | null;
  next_follow: string | null;
  remarks: string | null;
  files: FileRef[];
}

export interface MarketingInfo {
  potential: string;
  dm_name: string;
  dm_desig: string | null;
  dm_mobile: string | null;
  dm_email: string | null;
  competitor: string | null;
  exp_qty: number | null;
  decision_date: string | null;
  stage: string | null;
  remarks: string | null;
  next_action: string | null;
  next_follow: string | null;
  person: string;
  overdue: boolean;
}

export interface Followup {
  id: Id;
  at: string;
  method: string;
  person: string;
  summary: string;
  next_action: string | null;
  next_date: string | null;
  by: string;
  /* GET /followups only */
  request_id?: Id;
  school?: string;
}

export interface OrderInfo {
  ay: string;
  po: string;
  series: string[];
  classes: string[];
  subjects: string[];
  qty: number;
  conf_date: string | null;
  del_date: string | null;
  payment: string;
  remarks: string | null;
  source: 'myjo' | 'distributor';
}

export interface DistOrder {
  status: 'Submitted' | 'Returned' | 'Rejected' | 'Accepted';
  direct: boolean;
  ay: string;
  po: string;
  series: string[];
  classes: string[];
  subjects: string[];
  qty: number;
  req_delivery: string | null;
  remarks: string | null;
  files: FileRef[];
  by: string;
  at: string;
  review_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface Coverage {
  training: boolean;
  papers: boolean;
  resources: boolean;
  complete: boolean;
  missing: string[];
}

export interface AcademicInfo {
  eligible: boolean;
  coverage: Coverage;
  trainings: { id: Id; no: string; title: string; status: string; at: string }[];
  papers: { id: Id; no: string; status: string; cls: string; subject: string; exam: string }[];
  resources_count: number;
  pack: { at: string; by: string; training_id: Id | null; paper_ids: Id[]; resource_ids: Id[] } | null;
  login: { username: string; active: boolean } | null;
}

export interface CancelInfo {
  reason: string;
  by: string;
  at?: string;
  approved_by: string | null;
}

export interface AuditEntry {
  at: string;
  user: string;
  action: string;
  field: string | null;
  old: string | null;
  new: string | null;
  /* GET /audit only */
  entity?: string;
  ref?: string;
}

export interface RequestDetail extends RequestListItem {
  remarks: string | null;
  classes: string[];
  subjects: string[];
  series: string[];
  exp_qty: number | null;
  notes: Note[];
  schedule: Schedule | null;
  /** null for distributors */
  feedback: Feedback | null;
  /** null for distributors */
  marketing: MarketingInfo | null;
  /** empty for distributors */
  followups: Followup[];
  order: OrderInfo | null;
  dist_order: DistOrder | null;
  academic: AcademicInfo | null;
  cancel: CancelInfo | null;
  steps: { label: string; done: boolean; stopped: boolean }[];
  /** only for roles with seeInternal */
  audit?: AuditEntry[];
  actions: RequestAction[];
}

/* ---------- marketing & orders ---------- */

export interface MarketingRow {
  id: Id;
  no: string;
  school: SchoolInfo;
  distributor: Party;
  status: string;
  order_status: string | null;
  dist_order_status: string | null;
  potential: string | null;
  person: string | null;
  stage: string | null;
  next_follow: string | null;
  next_action: string | null;
  overdue: boolean;
  exp_qty: number | null;
}

export interface ConfirmedOrderRow {
  request_id: Id;
  no: string;
  school: string;
  city: string;
  distributor: string;
  ay: string;
  series: string[];
  classes: string[];
  subjects: string[];
  qty: number;
  po: string;
  conf_date: string | null;
  del_date: string | null;
  payment: string;
  order_status: string;
  source: string;
}

export interface PendingDistRow {
  request_id: Id;
  school: string;
  distributor: string;
  po: string;
  series: string[];
  qty: number;
  at: string;
  req_delivery: string | null;
}

export interface OrdersOverview {
  confirmed: ConfirmedOrderRow[];
  pending_dist: PendingDistRow[];
  status_counts: Record<string, number>;
  totals: { schools: number; books: number };
}

export interface CanOrderRow {
  id: Id;
  school: string;
  city: string;
  status: string;
  dist_order_status: string | null;
  review_note: string | null;
}

export interface MyOrderRow {
  /** request id */
  id: Id;
  school: string;
  po: string;
  series: string[];
  qty: number;
  placed: string | null;
  delivery: string | null;
  status: string;
  by_myjo: boolean;
}

export interface MyOrders {
  can_order: CanOrderRow[];
  orders: MyOrderRow[];
  kpis: { confirmed: number; waiting: number; returned: number; books: number };
  final_orders: boolean;
}

/* ---------- academic ---------- */

export interface OrderedSchool {
  request_id: Id;
  no: string;
  school: string;
  city: string;
  distributor: string;
  order: {
    /** "Confirmed" for final orders, otherwise awaiting Myjo */
    status: string;
    source: string;
    date: string | null;
    po: string;
    qty: number;
    series: string[];
    classes: string[];
    subjects: string[];
  };
  counts: { trainings: number; papers: number; resources: number };
  coverage: Coverage;
  login_active: boolean;
}

export interface TrainingSchoolBrief {
  request_id: Id;
  name: string;
  expected: number;
  attended: number | null;
}

export interface TrainingListItem {
  id: Id;
  no: string;
  title: string;
  type: string;
  ay: string;
  at: string;
  mode: string;
  trainer: string;
  status: string;
  schools: TrainingSchoolBrief[];
  expected_total: number;
  attended_total: number;
  overdue: boolean;
  cancel_pending: boolean;
}

export interface SchoolFeedback {
  rating: number;
  text: string;
  attended: number | null;
  by: string;
  at: string;
}

export interface TrainingSchool {
  request_id: Id;
  name: string;
  city: string;
  expected: number;
  school_confirm: string | null;
  school_teachers: number | null;
  attended: number | null;
  attendance: string | null;
  myjo_feedback: string | null;
  school_feedback: SchoolFeedback | null;
}

export interface Completion {
  status: string;
  trainer_remarks: string;
  follow_up: string;
  recording: string;
  files: FileRef[];
  at: string;
  by: string;
}

export interface TrainingHistory {
  at: string;
  by: string;
  school: string;
  action: string;
}

export type TrainingAction = 'edit' | 'schedule' | 'complete' | 'close' | 'cancel';

export interface ResourceBrief {
  id: Id;
  no: string;
  title: string;
  type: string;
  version: string;
  status: string;
}

export interface TrainingDetail extends Omit<TrainingListItem, 'schools'> {
  series: string[];
  classes: string[];
  subjects: string[];
  link: string | null;
  venue: string | null;
  agenda: string;
  remarks: string | null;
  instructions: string | null;
  schools: TrainingSchool[];
  resources: ResourceBrief[];
  completion: Completion | null;
  history: TrainingHistory[];
  cancel: CancelInfo | null;
  actions: TrainingAction[];
}

export type PaperAction = 'edit' | 'publish' | 'deliver' | 'revoke' | 'restore' | 'cancel';

export interface Paper {
  id: Id;
  no: string;
  request_id: Id;
  school: string;
  ay: string;
  cls: string;
  subject: string;
  series: string;
  exam: string;
  due_date: string;
  assignee: string | null;
  max_marks: number | null;
  delivery_date: string | null;
  remarks: string | null;
  status: string;
  qp_file: FileRef | null;
  ak_file: FileRef | null;
  revoked: boolean;
  raised_by: string;
  published_at: string | null;
  overdue: boolean;
  cancel_pending: boolean;
  actions: PaperAction[];
}

export type ResourceAction = 'edit' | 'publish' | 'archive' | 'access' | 'cancel';

export interface Resource {
  id: Id;
  no: string;
  title: string;
  type: string;
  series: string;
  cls: string;
  subject: string;
  ay: string;
  description: string | null;
  file: FileRef | null;
  link: string | null;
  version: string;
  upload_date: string;
  uploaded_by: string;
  access: 'All Ordered Schools' | 'Selected Schools Only';
  school_ids: Id[];
  /** school names for school_ids */
  schools: string[];
  revoked_ids: Id[];
  /** school names for revoked_ids */
  revoked: string[];
  /** schools that can see it (before revocations) */
  audience: { id: Id; name: string }[];
  status: string;
  downloads: number;
  cancel_pending: boolean;
  actions: ResourceAction[];
}

export interface DownloadLog {
  at: string;
  request_id?: Id;
  school?: string;
  user: string;
  kind: string;
  item: string;
  file: string;
}

export interface Downloads {
  by_school: DownloadsBySchool[];
  log: DownloadLog[];
}

/* ---------- school portal ---------- */

export interface PortalOrder {
  status: 'Confirmed' | 'Awaiting';
  ay: string;
  po: string;
  series: string[];
  classes: string[];
  subjects: string[];
  qty: number;
  delivery: string | null;
}

export interface PortalOverview {
  school: { name: string; city: string; state: string; board: string };
  order: PortalOrder;
  upcoming_trainings: { id: Id; title: string; at: string; mode: string; trainer: string; expected: number; confirm: string | null }[];
  updates: { at: string; event: string; message: string }[];
  kpis: { upcoming: number; papers: number; resources: number; my_downloads: number };
}

/** A resource as a school sees it (portal library / training). */
export interface PortalResource {
  id: Id;
  no: string;
  title: string;
  type: string;
  series: string;
  cls: string;
  subject: string;
  ay: string;
  description: string | null;
  version: string;
  file: FileRef | null;
  link: string | null;
}

export interface PortalTraining {
  id: Id;
  no: string;
  title: string;
  type: string;
  status: string;
  at: string;
  mode: string;
  /** only while Scheduled */
  link: string | null;
  venue: string | null;
  trainer: string;
  trainer_contact: string | null;
  series: string[];
  classes: string[];
  subjects: string[];
  agenda: string;
  instructions: string | null;
  mine: {
    expected: number;
    confirm: string | null;
    teachers: number | null;
    attended: number | null;
    attendance: string | null;
    feedback: { rating: number; text: string } | null;
  };
  resources: PortalResource[];
  can_confirm: boolean;
  can_feedback: boolean;
}

export interface PortalPaper {
  id: Id;
  no: string;
  cls: string;
  subject: string;
  series: string;
  exam: string;
  ay: string;
  max_marks: number | null;
  published_at: string | null;
  qp_file: FileRef | null;
  ak_file: FileRef | null;
}

export interface PortalLibrary {
  papers: PortalPaper[];
  resources: PortalResource[];
  /** the school's ordered series */
  series: string[];
}

export interface PortalRequest {
  id: Id;
  no: string;
  cls: string;
  subject: string;
  exam: string;
  due_date: string;
  /** already simplified for schools: New / In Progress / Published / Closed */
  status: string;
}

/* ---------- admin ---------- */

export interface ManagedUser extends User {
  active: boolean;
  locked: boolean;
  /** still on a temporary password/PIN */
  temporary: boolean;
}

export interface PermissionGrid {
  roles: { code: Role; label: string }[];
  screens: { code: string; label: string; eligible: Record<string, boolean> }[];
  actions: { code: string; label: string; eligible: Record<string, boolean> }[];
  granted: { screens: Record<string, string[]>; actions: Record<string, string[]> };
}

export interface MasterSeries {
  id: Id;
  name: string;
  color: string;
  active: boolean;
  used: number;
}

export interface MasterSubject {
  id: Id;
  name: string;
  active: boolean;
  used: number;
}

export interface Masters {
  series: MasterSeries[];
  subjects: MasterSubject[];
}

export interface NotificationEntry {
  at: string;
  event: string;
  message: string;
  recipients: { name: string; email?: string | null; phone?: string | null }[];
  ref: string | null;
  channel: string;
  status: string;
}

/* ---------- reports ---------- */

export interface ReportInfo {
  key: string;
  name: string;
}

export interface ReportResult {
  name: string;
  columns: { label: string; type: 'text' | 'number' }[];
  rows: (string | number | null)[][];
  total: (string | number | null)[] | null;
}
