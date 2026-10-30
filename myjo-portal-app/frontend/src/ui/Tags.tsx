/* Series tags (coloured spine marker) and file chips. */
import { useState, type ReactNode } from 'react';
import { downloadFile, toApiError } from '../api';
import { fileSize } from '../format';
import { useAuth } from '../auth';
import { useMetaState } from '../meta';
import type { FileRef } from '../types';
import { useToast } from './Toast';

export function SeriesTag({ name }: { name: string }) {
  const { meta } = useMetaState();
  const color = meta?.all_series_colors[name] ?? meta?.series.find((s) => s.name === name)?.color ?? '#888';
  return (
    <span className="tag">
      <i className="spine" style={{ background: color }} aria-hidden="true" />
      {name}
    </span>
  );
}

export function SeriesTags({ names }: { names?: readonly string[] | string | null }) {
  const arr = names ? ([] as string[]).concat(names) : [];
  if (!arr.length) return <>—</>;
  return (
    <div className="tags">
      {arr.map((n) => (
        <SeriesTag key={n} name={n} />
      ))}
    </div>
  );
}

/** Downloads a stored file with the bearer token; `context` is the API download context. */
export function DownloadButton({ file, context, children, className = 'btn sm primary' }: { file: FileRef; context: string; children: ReactNode; className?: string }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try {
      await downloadFile(file, context);
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    } finally {
      setBusy(false);
    }
  };
  return (
    <button type="button" className={className} onClick={run} disabled={busy} aria-busy={busy}>
      {busy ? 'Downloading…' : children}
    </button>
  );
}

/** Staff (every role except distributor and school) may download any file without a context. */
export function useStaffDownloads(): boolean {
  const { user } = useAuth();
  return !!user && user.role !== 'dist' && user.role !== 'school';
}

/**
 * File chips. Names become download buttons when `context` is given (paper/resource files)
 * or when `staff` is true (attachments such as PO copies, which staff download without a context).
 */
export function FileChips({ files, context, staff }: { files?: (FileRef | null | undefined)[] | null; context?: (f: FileRef) => string; staff?: boolean }) {
  const toast = useToast();
  const canDownload = !!context || !!staff;
  const list = (files ?? []).filter((f): f is FileRef => !!f);
  if (!list.length) return <span className="muted">No files</span>;
  return (
    <div className="files">
      {list.map((f) => (
        <span className="file" key={String(f.id) + f.name}>
          {canDownload ? (
            <button type="button" aria-label={'Download ' + f.name} onClick={() => downloadFile(f, context?.(f)).catch((e: unknown) => toast(toApiError(e).message, 'bad'))}>
              {f.name}
            </button>
          ) : (
            f.name
          )}
          {f.size ? <span className="muted">{fileSize(f.size)}</span> : null}
        </span>
      ))}
    </div>
  );
}
