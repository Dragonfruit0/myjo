import { Link } from 'react-router-dom';
import { linkPath } from '../nav';
import type { DashKpi, ScreenLink } from '../types';

/** Maps API tones to the prototype's KPI styles (hl = highlighted good, alert = red value). */
function kpiClass(tone?: string | null): string {
  if (!tone) return '';
  if (['hl', 'good', 'highlight', 'success'].includes(tone)) return ' hl';
  if (['alert', 'bad', 'danger', 'warn'].includes(tone)) return ' alert';
  return '';
}

export function Kpi({ value, label, link, tone }: { value: number | string; label: string; link?: string | ScreenLink; tone?: string | null }) {
  const v = typeof value === 'number' ? value.toLocaleString('en-IN') : value;
  const body = (
    <>
      <span className="v">{v}</span>
      <span className="l">{label}</span>
    </>
  );
  if (!link) return <div className={'kpi' + kpiClass(tone)}>{body}</div>;
  return (
    <Link className={'kpi' + kpiClass(tone)} to={linkPath(link)}>
      {body}
    </Link>
  );
}

export function KpiRow({ kpis }: { kpis: DashKpi[] }) {
  return (
    <div className="kpis">
      {kpis.map((k) => (
        <Kpi key={k.group + k.label} value={k.value} label={k.label} link={k.link} tone={k.tone} />
      ))}
    </div>
  );
}

/** KPIs grouped by `group`, keeping the server's order. */
export function KpiGroups({ kpis }: { kpis: DashKpi[] }) {
  const groups: { name: string; items: DashKpi[] }[] = [];
  for (const k of kpis) {
    let g = groups.find((x) => x.name === k.group);
    if (!g) groups.push((g = { name: k.group, items: [] }));
    g.items.push(k);
  }
  return (
    <>
      {groups.map((g) => (
        <div className="kgroup" key={g.name}>
          {g.name && <h2>{g.name}</h2>}
          <KpiRow kpis={g.items} />
        </div>
      ))}
    </>
  );
}
