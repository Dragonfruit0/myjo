/* Status pills. Tones follow the prototype's TONE table. */
const TONE: Record<'good' | 'info' | 'warn' | 'bad', string[]> = {
  good: ['Complete', 'Accepted', 'Confirmed', 'Attended', 'Converted', 'Order Confirmed', 'Completed', 'Published', 'Delivered', 'Approved', 'Paid', 'High', 'Active', 'Downloadable', 'Sent', 'Always'],
  info: ['Returned', 'Partially attended', 'Partially completed', 'Under Review', 'Demo Scheduled', 'Scheduled', 'Assigned', 'In Progress', 'Ready for Review', 'Quotation Sent', 'Sample Sent', 'Under Discussion', 'Demo Completed', 'Partially Confirmed', 'Advance Received', 'Partially Paid', 'Medium', 'Follow-up Pending'],
  warn: ['Submitted', 'Temporary login', 'Awaiting', 'New', 'On Hold', 'Pending', 'Draft', 'Cancellation pending', 'Not shared yet', 'Not confirmed yet'],
  bad: ['Missing', 'Locked', 'Declined', 'Did not attend', 'Rejected', 'Not Converted', 'Lost to Competitor', 'Not Interested', 'Cancelled', 'Low', 'Revoked', 'Overdue', 'Inactive', 'No downloads', 'Failed'],
};

export type Tone = 'good' | 'info' | 'warn' | 'bad' | 'neutral';

export function toneOf(s: string): Tone {
  for (const k of Object.keys(TONE) as (keyof typeof TONE)[]) if (TONE[k].includes(s)) return k;
  return 'neutral';
}

export function Pill({ s, tone }: { s?: string | null; tone?: Tone }) {
  if (!s) return <span className="muted">—</span>;
  return <span className={'pill ' + (tone ?? toneOf(s))}>{s}</span>;
}

/** Status pill plus the extra "Cancellation pending" / "Overdue" pills used across lists. */
export function StatusPills({ status, cancelled, cancelPending, overdue }: { status: string; cancelled?: boolean; cancelPending?: boolean; overdue?: boolean }) {
  return (
    <>
      <Pill s={cancelled ? 'Cancelled' : status} />
      {cancelPending && !cancelled && <> <Pill s="Cancellation pending" /></>}
      {overdue && <> <Pill s="Overdue" /></>}
    </>
  );
}
