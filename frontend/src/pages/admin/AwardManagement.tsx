import React, { useEffect, useState } from 'react';
import { api } from '../../api/client';
import { AwardItem } from '../../api/types';
import { RefreshCw, Save, Send } from 'lucide-react';

export const AwardManagement: React.FC = () => {
  const [awards, setAwards] = useState<AwardItem[]>([]);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<Record<number, { status: string; amount: string; start: string; end: string; review: string; remarks: string }>>({});
  const [paymentDrafts, setPaymentDrafts] = useState<Record<number, { period: string; amount: string; reference: string }>>({});

  const load = async () => {
    setError('');
    try {
      const rows = await api.getAwards();
      setAwards(rows);
      setDrafts(Object.fromEntries(rows.map((award) => [award.id, {
        status: award.award_status,
        amount: award.approved_amount == null ? '' : String(award.approved_amount),
        start: award.start_date?.slice(0, 10) || '',
        end: award.end_date?.slice(0, 10) || '',
        review: award.next_review_date?.slice(0, 10) || '',
        remarks: award.officer_remarks || ''
      }])));
      setPaymentDrafts(Object.fromEntries(rows.map((award) => [award.id, { period: '', amount: '', reference: '' }])));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to load award records.');
    }
  };
  useEffect(() => { void load(); }, []);

  const updateAward = async (award: AwardItem) => {
    const draft = drafts[award.id];
    setBusyId(award.id);
    setError('');
    try {
      await api.updateAward(award.application_id, {
        award_status: draft.status,
        ...(draft.amount ? { approved_amount: Number(draft.amount) } : {}),
        ...(draft.start ? { start_date: `${draft.start}T00:00:00` } : {}),
        ...(draft.end ? { end_date: `${draft.end}T00:00:00` } : {}),
        ...(draft.review ? { next_review_date: `${draft.review}T00:00:00` } : {}),
        officer_remarks: draft.remarks
      });
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to update award.');
    } finally {
      setBusyId(null);
    }
  };

  const addPayment = async (award: AwardItem) => {
    const draft = paymentDrafts[award.id];
    setBusyId(award.id);
    setError('');
    try {
      await api.addPayment(award.id, {
        period: draft.period,
        amount: Number(draft.amount),
        status: 'PENDING',
        reference: draft.reference
      });
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to add payment milestone.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-5">
      <header className="flex justify-between items-start">
        <div><p className="text-xs font-bold uppercase text-emerald-800">Post-selection workflow</p><h2 className="text-2xl font-bold text-slate-900">Award and fellowship monitoring</h2><p className="text-sm text-slate-600 mt-1">Track approval amount, award lifecycle, review dates and payment milestones. No money is transferred by this prototype.</p></div>
        <button onClick={() => void load()} className="flex items-center gap-2 px-3 py-2 bg-white border rounded-lg text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
      </header>
      {error && <p role="alert" className="text-sm text-rose-700 bg-rose-50 border border-rose-200 p-3 rounded">{error}</p>}
      {awards.length === 0 && <div className="bg-white border rounded-xl p-8 text-center text-slate-600">Approved applications will appear here.</div>}
      <div className="space-y-4">
        {awards.map((award) => {
          const draft = drafts[award.id];
          const payment = paymentDrafts[award.id];
          if (!draft || !payment) return null;
          return <article key={award.id} className="bg-white border rounded-xl p-5 space-y-4">
            <div className="flex flex-wrap justify-between gap-2 border-b pb-3">
              <div><div className="font-mono text-xs text-slate-500">{award.application_no} · {award.scheme_code}</div><h3 className="font-bold text-slate-900">{award.applicant_name}</h3></div>
              <span className="text-xs px-2 py-1 rounded bg-emerald-50 text-emerald-800">{award.award_status}</span>
            </div>
            <div className="grid sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <label className="text-xs font-semibold">Lifecycle status<select value={draft.status} onChange={(e) => setDrafts((old) => ({ ...old, [award.id]: { ...draft, status: e.target.value } }))} className="block mt-1 w-full border rounded px-2 py-2"><option>ACTIVE</option><option>ON_HOLD</option><option>COMPLETED</option><option>TERMINATED</option></select></label>
              <label className="text-xs font-semibold">Approved amount (INR)<input type="number" min="0" value={draft.amount} onChange={(e) => setDrafts((old) => ({ ...old, [award.id]: { ...draft, amount: e.target.value } }))} className="block mt-1 w-full border rounded px-2 py-2" /></label>
              <label className="text-xs font-semibold">Start date<input type="date" value={draft.start} onChange={(e) => setDrafts((old) => ({ ...old, [award.id]: { ...draft, start: e.target.value } }))} className="block mt-1 w-full border rounded px-2 py-2" /></label>
              <label className="text-xs font-semibold">End date<input type="date" value={draft.end} onChange={(e) => setDrafts((old) => ({ ...old, [award.id]: { ...draft, end: e.target.value } }))} className="block mt-1 w-full border rounded px-2 py-2" /></label>
              <label className="text-xs font-semibold">Next review<input type="date" value={draft.review} onChange={(e) => setDrafts((old) => ({ ...old, [award.id]: { ...draft, review: e.target.value } }))} className="block mt-1 w-full border rounded px-2 py-2" /></label>
              <label className="text-xs font-semibold">Officer note<input value={draft.remarks} onChange={(e) => setDrafts((old) => ({ ...old, [award.id]: { ...draft, remarks: e.target.value } }))} className="block mt-1 w-full border rounded px-2 py-2" /></label>
            </div>
            <button disabled={busyId === award.id} onClick={() => void updateAward(award)} className="flex items-center gap-2 px-3 py-2 rounded bg-blue-900 text-white text-xs disabled:opacity-50"><Save className="w-4 h-4" /> Save award record</button>
            <div className="border-t pt-3">
              <h4 className="text-sm font-bold mb-2">Payment milestones (manual records)</h4>
              {award.payments.length > 0 && <ul className="text-xs divide-y mb-3">{award.payments.map((item) => <li key={item.id} className="py-2 flex justify-between"><span>{item.period} · {item.reference || 'No reference'}</span><span>{award.currency} {item.amount.toLocaleString()} · {item.status}</span></li>)}</ul>}
              <div className="grid sm:grid-cols-4 gap-2 items-end">
                <input aria-label="Payment period" placeholder="Period / instalment" value={payment.period} onChange={(e) => setPaymentDrafts((old) => ({ ...old, [award.id]: { ...payment, period: e.target.value } }))} className="border rounded px-2 py-2 text-xs" />
                <input aria-label="Payment amount" type="number" min="0.01" placeholder="Amount INR" value={payment.amount} onChange={(e) => setPaymentDrafts((old) => ({ ...old, [award.id]: { ...payment, amount: e.target.value } }))} className="border rounded px-2 py-2 text-xs" />
                <input aria-label="Payment reference" placeholder="Reference (optional)" value={payment.reference} onChange={(e) => setPaymentDrafts((old) => ({ ...old, [award.id]: { ...payment, reference: e.target.value } }))} className="border rounded px-2 py-2 text-xs" />
                <button disabled={busyId === award.id || !payment.period || !payment.amount} onClick={() => void addPayment(award)} className="flex items-center justify-center gap-2 px-3 py-2 rounded bg-emerald-700 text-white text-xs disabled:opacity-50"><Send className="w-4 h-4" /> Add pending record</button>
              </div>
            </div>
          </article>;
        })}
      </div>
    </section>
  );
};
