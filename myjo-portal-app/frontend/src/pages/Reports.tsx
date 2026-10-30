/*
 * Reports: GET /reports (list), GET /reports/<key>?filters (table), and export through
 * GET /reports/<key>/export?format=xlsx|pdf|csv&filters (downloaded as a blob with the bearer token).
 */
import { useMemo, useState } from 'react';
import { asList, download, toApiError, type Query } from '../api';
import { num, pad } from '../format';
import { useApi, useDebounced } from '../hooks';
import { useMeta } from '../meta';
import type { ListResponse, ReportInfo, ReportResult, RequestListItem } from '../types';
import { Async, Loading } from '../ui/Async';
import { Card, PageHead } from '../ui/Card';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

type FilterKey = 'from' | 'to' | 'school' | 'distributor' | 'city' | 'state' | 'ay' | 'series' | 'cls' | 'subject' | 'status' | 'employee' | 'marketing' | 'presenter' | 'trainer';

const FILTERS: [FilterKey, string, 'date' | 'select'][] = [
  ['from', 'From date', 'date'], ['to', 'To date', 'date'], ['school', 'School', 'select'], ['distributor', 'Distributor', 'select'],
  ['city', 'City', 'select'], ['state', 'State', 'select'], ['ay', 'Academic year', 'select'], ['series', 'Book series', 'select'],
  ['cls', 'Class', 'select'], ['subject', 'Subject', 'select'], ['status', 'Status', 'select'], ['employee', 'Assigned employee', 'select'],
  ['marketing', 'Marketing person', 'select'], ['presenter', 'Presenter', 'select'], ['trainer', 'Trainer', 'select'],
];

const uniq = (a: string[]) => [...new Set(a.filter(Boolean))].sort();

function cell(v: string | number | null, numeric: boolean) {
  if (v === null || v === '') return '—';
  return numeric && typeof v === 'number' ? num(v) : String(v);
}

export default function Reports() {
  const meta = useMeta();
  const toast = useToast();
  const list = useApi<ReportInfo[] | ListResponse<ReportInfo>>('/reports');
  const reqs = useApi<RequestListItem[] | ListResponse<RequestListItem>>('/requests');
  const reports = asList(list.data);
  const [picked, setPicked] = useState('');
  const key = picked || reports[0]?.key || '';
  const [filters, setFilters] = useState<Partial<Record<FilterKey, string>>>({});
  const query = useDebounced<Query>(filters, 250);
  const result = useApi<ReportResult>(key ? `/reports/${encodeURIComponent(key)}` : null, query);
  const [exporting, setExporting] = useState<string | null>(null);

  const options = useMemo(() => {
    const rs = asList(reqs.data);
    const people = uniq([...meta.people.demo, ...meta.people.mkt, ...meta.people.acad]);
    const o: Record<FilterKey, [string, string][]> = {
      from: [], to: [],
      school: rs.map((r) => [String(r.id), r.school.name]),
      distributor: meta.distributors.map((d) => [String(d.id), d.name]),
      city: uniq(rs.map((r) => r.school.city)).map((c) => [c, c]),
      state: uniq(rs.map((r) => r.school.state)).map((c) => [c, c]),
      ay: meta.academic_years.map((x) => [x, x]),
      series: meta.series.map((s) => [s.name, s.name]),
      cls: meta.classes.map((x) => [x, x]),
      subject: meta.subjects.map((x) => [x, x]),
      status: uniq([...meta.request_statuses, ...meta.order_statuses, ...meta.training_statuses, ...meta.paper_statuses, ...meta.resource_statuses]).map((x) => [x, x]),
      employee: people.map((x) => [x, x]),
      marketing: meta.people.mkt.map((x) => [x, x]),
      presenter: meta.people.demo.map((x) => [x, x]),
      trainer: meta.people.acad.map((x) => [x, x]),
    };
    return o;
  }, [reqs.data, meta]);

  const setF = (k: FilterKey, v: string) => setFilters((f) => ({ ...f, [k]: v }));

  const exportAs = async (format: 'xlsx' | 'pdf' | 'csv') => {
    if (!key) return;
    setExporting(format);
    try {
      await download(`/reports/${encodeURIComponent(key)}/export`, { format, ...filters }, `${key}.${format}`);
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    } finally {
      setExporting(null);
    }
  };

  const exportBtn = (format: 'xlsx' | 'pdf' | 'csv', label: string, primary = false) => (
    <button type="button" className={'btn' + (primary ? ' primary' : '')} onClick={() => void exportAs(format)} disabled={!key || !!exporting} aria-busy={exporting === format}>
      {exporting === format ? 'Preparing…' : label}
    </button>
  );

  return (
    <>
      <PageHead
        title="Reports"
        sub="Detailed and summary reports. Filters that don’t apply to a report are ignored."
        actions={
          <>
            {exportBtn('xlsx', 'Export Excel', true)}
            {exportBtn('pdf', 'Export PDF')}
            {exportBtn('csv', 'Export CSV')}
            <button type="button" className="btn" onClick={() => setFilters({})}>
              Clear filters
            </button>
          </>
        }
      />
      <Async state={list}>
        {() => (
          <Card title="Report & filters">
            <div className="rf">
              <label style={{ gridColumn: '1/-1' }}>
                Report
                <select value={key} onChange={(e) => setPicked(e.target.value)}>
                  {reports.map((r, i) => (
                    <option key={r.key} value={r.key}>
                      {pad(i + 1)} · {r.name}
                    </option>
                  ))}
                </select>
              </label>
              {FILTERS.map(([k, label, t]) => (
                <label key={k}>
                  {label}
                  {t === 'date' ? (
                    <input type="date" value={filters[k] ?? ''} onChange={(e) => setF(k, e.target.value)} />
                  ) : (
                    <select value={filters[k] ?? ''} onChange={(e) => setF(k, e.target.value)}>
                      <option value="">All</option>
                      {options[k].map(([v, l]) => (
                        <option key={v} value={v}>
                          {l}
                        </option>
                      ))}
                    </select>
                  )}
                </label>
              ))}
            </div>
          </Card>
        )}
      </Async>
      {key && (
        <Async state={result}>
          {(r) => {
            const numeric = r.columns.map((c) => c.type === 'number');
            return (
              <div className="stack" style={{ gap: 8 }}>
                <p className="muted" aria-live="polite">
                  {r.rows.length} row{r.rows.length === 1 ? '' : 's'} · {r.name}
                  {result.loading && ' · updating…'}
                </p>
                <Table
                  columns={r.columns.map((c, i) => ({ label: c.label, n: numeric[i], render: (row: (string | number | null)[]) => cell(row[i], numeric[i]) }))}
                  rows={r.rows}
                  rowKey={(_, i) => i}
                  total={r.total && r.rows.length ? r.total.map((v, i) => (i === 0 && (v === null || v === '') ? 'Total' : cell(v, numeric[i]))) : undefined}
                  empty="No records match these filters."
                  caption={r.name}
                />
              </div>
            );
          }}
        </Async>
      )}
      {!key && list.data && <Loading label="No reports available." />}
    </>
  );
}
