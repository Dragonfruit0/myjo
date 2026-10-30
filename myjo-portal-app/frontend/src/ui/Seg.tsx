/* Segmented status filter ("All", "Draft", "Scheduled" …). */
export function Seg({ options, value, onChange, label, allLabel = 'All' }: { options: string[]; value: string; onChange: (v: string) => void; label: string; allLabel?: string }) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {['', ...options].map((s) => (
        <button key={s || '_all'} type="button" className={value === s ? 'on' : undefined} aria-pressed={value === s} onClick={() => onChange(s)}>
          {s || allLabel}
        </button>
      ))}
    </div>
  );
}
