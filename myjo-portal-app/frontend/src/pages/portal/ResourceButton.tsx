/*
 * Download / open a resource from the school portal.
 * Files: GET /files/<id>/download?context=resource:<id> (recorded by the server).
 * Video links: POST /portal/resources/<id>/open records the view and returns the link.
 */
import { useState } from 'react';
import { post, toApiError } from '../../api';
import type { PortalResource } from '../../types';
import { DownloadButton } from '../../ui/Tags';
import { useToast } from '../../ui/Toast';
import { resourceContext } from '../Resources';

function OpenVideoButton({ resource }: { resource: PortalResource }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const open = async () => {
    // Open the tab synchronously (so pop-up blockers allow it), then point it at the link.
    const win = window.open('', '_blank');
    if (win) win.opener = null;
    setBusy(true);
    try {
      const { link } = await post<{ link: string }>(`/portal/resources/${resource.id}/open`);
      if (win) win.location.href = link;
      else window.open(link, '_blank', 'noopener,noreferrer');
    } catch (e) {
      win?.close();
      toast(toApiError(e).message, 'bad');
    } finally {
      setBusy(false);
    }
  };
  return (
    <button type="button" className="btn sm primary" onClick={() => void open()} disabled={busy} aria-busy={busy}>
      {busy ? 'Opening…' : 'Open video'}
    </button>
  );
}

export function ResourceButton({ resource }: { resource: PortalResource }) {
  if (resource.link) return <OpenVideoButton resource={resource} />;
  if (resource.file)
    return (
      <DownloadButton file={resource.file} context={resourceContext(resource)}>
        Download
      </DownloadButton>
    );
  return <span className="muted">—</span>;
}
