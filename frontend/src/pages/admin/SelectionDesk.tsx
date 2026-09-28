import React, { useEffect, useState } from 'react';
import { api } from '../../api/client';
import { Scheme, SelectionResult } from '../../api/types';
import { AlertTriangle, Eye, RefreshCw } from 'lucide-react';

interface SelectionDeskProps {
  onSelectApplication: (id: number) => void;
}

export const SelectionDesk: React.FC<SelectionDeskProps> = ({ onSelectApplication }) => {
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [schemeCode, setSchemeCode] = useState('NFST');
  const [slots, setSlots] = useState(10);
  const [result, setResult] = useState<SelectionResult | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getSchemes().then((items) => {
      setSchemes(items);
      if (!items.some((item) => item.code === schemeCode) && items[0]) setSchemeCode(items[0].code);
    }).catch((err: unknown) => setError(err instanceof Error ? err.message : 'Unable to load schemes.'));
  }, []);

  const loadRankings = async () => {
    setError('');
    try {
      setResult(await api.getSelection(schemeCode, slots));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to load the ranking aid.');
    }
  };

  useEffect(() => {
    if (schemes.length) void loadRankings();
  }, [schemeCode, schemes]);

  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-5">
      <header>
        <p className="text-xs font-bold uppercase text-emerald-800">Officer workspace</p>
        <h2 className="text-2xl font-bold text-slate-900">Merit and selection support</h2>
        <p className="text-sm text-slate-600 mt-1">Transparent marks-based ranking aid. It never selects or rejects applicants automatically.</p>
      </header>
      <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 text-sm text-amber-900 flex gap-2">
        <AlertTriangle className="w-5 h-5 shrink-0" />
        <span>{result?.notice || 'Verify current scheme rules, category roster, quotas and every document before recording an authorized human decision.'}</span>
      </div>
      <div className="flex flex-wrap items-end gap-3 bg-white border rounded-xl p-4">
        <label className="text-xs font-semibold text-slate-700">Scheme
          <select value={schemeCode} onChange={(event) => setSchemeCode(event.target.value)} className="block mt-1 border rounded-lg px-3 py-2">
            {schemes.map((scheme) => <option key={scheme.code} value={scheme.code}>{scheme.code} — {scheme.name}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-700">Available seats
          <input type="number" min="1" max="500" value={slots} onChange={(event) => setSlots(Math.max(1, Number(event.target.value) || 1))} className="block mt-1 border rounded-lg px-3 py-2 w-28" />
        </label>
        <button onClick={() => void loadRankings()} className="flex items-center gap-2 bg-blue-900 text-white rounded-lg px-4 py-2 text-sm">
          <RefreshCw className="w-4 h-4" /> Recalculate
        </button>
        {result?.mark_field && <span className="text-xs text-slate-600">Sorted by declared {result.mark_field.replace(/_/g, ' ')}. Values are not independently verified.</span>}
      </div>
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      <div className="overflow-x-auto bg-white border rounded-xl">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-600"><tr>
            <th className="p-3">Rank</th><th className="p-3">Application</th><th className="p-3">Applicant</th>
            <th className="p-3">Marks</th><th className="p-3">Preliminary checks</th><th className="p-3">Officer review</th>
          </tr></thead>
          <tbody className="divide-y">
            {(result?.candidates || []).map((candidate) => (
              <tr key={candidate.application_id}>
                <td className="p-3 font-bold">{candidate.rank ?? '—'}{candidate.within_available_slots && <span className="ml-2 text-[10px] text-emerald-800">within slots</span>}</td>
                <td className="p-3 font-mono">{candidate.application_no}</td>
                <td className="p-3">{candidate.applicant_name}<div className="text-xs text-slate-500">{candidate.status}</div></td>
                <td className="p-3">{candidate.marks ?? 'Not available'}</td>
                <td className="p-3">{candidate.eligible_for_ranking ? 'Rule checks pass; required document records present' : 'Not rankable pending checks, marks or documents'}</td>
                <td className="p-3"><button onClick={() => onSelectApplication(candidate.application_id)} className="flex items-center gap-1 text-blue-800 underline"><Eye className="w-4 h-4" /> Open file</button></td>
              </tr>
            ))}
            {!result?.candidates.length && <tr><td colSpan={6} className="p-6 text-center text-slate-500">No applications for this scheme.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
};
