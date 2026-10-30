/* Subjects & series (GET /masters; POST/PUT/DELETE /masters/<kind>[/<id>], POST …/toggle). */
import { del, post, put, toApiError } from '../api';
import { useApi } from '../hooks';
import { useMetaState } from '../meta';
import type { MasterSeries, MasterSubject, Masters } from '../types';
import { Async } from '../ui/Async';
import { Card, PageHead } from '../ui/Card';
import { vs } from '../ui/Form';
import { useModal } from '../ui/Modal';
import { Pill } from '../ui/Pill';
import { Table } from '../ui/Table';
import { useToast } from '../ui/Toast';

type Kind = 'series' | 'subjects';
type Item = MasterSeries | MasterSubject;
const ONE: Record<Kind, string> = { series: 'book series', subjects: 'subject' };
const LABEL: Record<Kind, string> = { series: 'Book series', subjects: 'Subject' };

export default function MastersPage() {
  const st = useApi<Masters>('/masters');
  const { reload: reloadMeta } = useMetaState();
  const modal = useModal();
  const toast = useToast();
  const done = () => {
    st.reload();
    reloadMeta();
  };

  const edit = (kind: Kind, x: Item | null) => {
    const isS = kind === 'series';
    const list: Item[] = st.data ? st.data[kind] : [];
    modal.form({
      title: (x ? 'Edit ' : 'Add ') + ONE[kind],
      sub: x ? `Renaming updates every record that uses “${x.name}”.` : undefined,
      fields: [
        { k: 'name', label: isS ? 'Series name' : 'Subject name', req: true, wide: true, ph: isS ? 'e.g. Myjo Art & Craft' : 'e.g. Art' },
        ...(isS ? [{ k: 'color', label: 'Spine colour', t: 'color' as const, hint: 'Shown as the marker beside the series name' }] : []),
      ],
      initial: x ? { ...x } : { color: '#4D7C8A' },
      submitLabel: x ? 'Save changes' : 'Add',
      validate: (v) => {
        const nm = vs(v, 'name').replace(/\s+/g, ' ');
        if (nm.length < 2) return 'Name must be at least 2 characters.';
        if (list.some((y) => y !== x && y.name.toLowerCase() === nm.toLowerCase())) return `“${nm}” already exists.`;
        return null;
      },
      onSubmit: async (v) => {
        const body = { name: vs(v, 'name').replace(/\s+/g, ' '), ...(isS ? { color: vs(v, 'color') } : {}) };
        if (x) await put(`/masters/${kind}/${x.id}`, body);
        else await post(`/masters/${kind}`, body);
        return `${LABEL[kind]} ${x ? 'updated' : 'added'}`;
      },
      onSuccess: done,
    });
  };

  const toggle = async (kind: Kind, x: Item) => {
    try {
      await post(`/masters/${kind}/${x.id}/toggle`);
      toast(x.name + (x.active ? ' deactivated' : ' activated'));
      done();
    } catch (e) {
      toast(toApiError(e).message, 'bad');
    }
  };

  const remove = (kind: Kind, x: Item) =>
    modal.form({
      title: 'Delete ' + ONE[kind],
      sub: `“${x.name}” is not used by any record. Deleting removes it from all lists.`,
      fields: [{ k: '_n', label: LABEL[kind], t: 'static', html: x.name }],
      submitLabel: 'Delete',
      danger: true,
      onSubmit: async () => {
        await del(`/masters/${kind}/${x.id}`);
        return `“${x.name}” deleted`;
      },
      onSuccess: done,
    });

  const actions = (kind: Kind, x: Item) => (
    <div className="row-actions">
      <button type="button" className="btn sm" onClick={() => edit(kind, x)}>Edit</button>
      <button type="button" className="btn sm" onClick={() => void toggle(kind, x)}>{x.active ? 'Deactivate' : 'Activate'}</button>
      <button type="button" className="btn sm danger" onClick={() => remove(kind, x)} disabled={x.used > 0} title={x.used > 0 ? 'In use: deactivate instead' : undefined}>
        Delete
      </button>
    </div>
  );

  return (
    <>
      <PageHead
        title="Subjects & series"
        sub="The lists used across demo requests, orders, training, question papers, resources, reports and the school library. Renaming updates every record. Items in use cannot be deleted; deactivate them to hide them from new entries."
      />
      <Async state={st}>
        {(d) => (
          <>
            <Card title="Book series" sub={`${d.series.filter((x) => x.active).length} active`} flush actions={<button type="button" className="btn primary" onClick={() => edit('series', null)}>Add series</button>}>
              <Table
                columns={[
                  { label: 'Series', render: (x) => <span className="tag"><i className="spine" style={{ background: x.color }} aria-hidden="true" />{x.name}</span> },
                  { label: 'Spine colour', render: (x) => <span className="mono">{x.color}</span> },
                  { label: 'Used in records', n: true, render: (x) => x.used },
                  { label: 'Status', render: (x) => <Pill s={x.active ? 'Active' : 'Inactive'} /> },
                  { label: 'Actions', render: (x) => actions('series', x) },
                ]}
                rows={d.series}
                rowKey={(x) => String(x.id)}
                empty="No series yet."
              />
            </Card>
            <Card title="Subjects" sub={`${d.subjects.filter((x) => x.active).length} active`} flush actions={<button type="button" className="btn primary" onClick={() => edit('subjects', null)}>Add subject</button>}>
              <Table
                columns={[
                  { label: 'Subject', render: (x) => x.name },
                  { label: 'Used in records', n: true, render: (x) => x.used },
                  { label: 'Status', render: (x) => <Pill s={x.active ? 'Active' : 'Inactive'} /> },
                  { label: 'Actions', render: (x) => actions('subjects', x) },
                ]}
                rows={d.subjects}
                rowKey={(x) => String(x.id)}
                empty="No subjects yet."
              />
            </Card>
          </>
        )}
      </Async>
    </>
  );
}
