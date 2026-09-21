import React, { useEffect, useState } from 'react';
import { api } from '../../api/client';
import { Scheme } from '../../api/types';
import { Award, Globe, CheckCircle2, ArrowRight, IndianRupee, Clock, BookOpen, AlertCircle } from 'lucide-react';

interface SchemeSelectionProps {
  onSelectScheme: (schemeCode: string) => void;
}

export const SchemeSelection: React.FC<SchemeSelectionProps> = ({ onSelectScheme }) => {
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSchemes();
  }, []);

  const fetchSchemes = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSchemes();
      setSchemes(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch schemes from backend');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-900 border-r-transparent mb-3" />
        <p className="text-sm text-slate-600">Loading MoTA scholarship schemes...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Backend Connection Issue</div>
            <p className="text-xs text-rose-700 mt-1">{error}</p>
            <p className="text-xs text-slate-500 mt-2">
              Ensure the FastAPI backend is running on <code>http://localhost:8000</code>.
            </p>
            <button
              onClick={fetchSchemes}
              className="mt-3 px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-medium"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="text-center max-w-2xl mx-auto mb-10">
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-900 border border-blue-200 uppercase tracking-wide">
          Ministry of Tribal Affairs Schemes
        </span>
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-950 mt-2">
          Fellowship & Scholarship Schemes for ST Students
        </h2>
        <p className="text-sm text-slate-600 mt-2">
          Select a scheme to view eligibility criteria and begin your AI-guided online application.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {schemes.map((s) => {
          const isNFST = s.code === 'NFST';
          return (
            <div
              key={s.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col justify-between"
            >
              {/* Card Header */}
              <div className="p-6 border-b border-slate-100">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div
                    className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                      isNFST ? 'bg-blue-900 text-amber-400' : 'bg-emerald-800 text-white'
                    }`}
                  >
                    {isNFST ? <Award className="w-6 h-6" /> : <Globe className="w-6 h-6" />}
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200">
                    CODE: {s.code}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-slate-900 leading-snug">{s.name}</h3>
                <p className="text-xs text-slate-600 mt-2 line-clamp-2">{s.description}</p>
              </div>

              {/* Key Specs Grid */}
              <div className="p-6 bg-slate-50/50 space-y-3 text-xs border-b border-slate-100">
                <div className="flex items-center justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                    Target Course Level
                  </span>
                  <span className="font-semibold text-slate-800">{s.degree_level}</span>
                </div>

                <div className="flex items-center justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <IndianRupee className="w-3.5 h-3.5 text-slate-400" />
                    Statutory Income Ceiling
                  </span>
                  <span className="font-semibold text-slate-800">
                    {s.max_income ? `≤ ₹${(s.max_income / 100000).toFixed(1)} Lakh / year` : 'No Cap'}
                  </span>
                </div>

                <div className="flex items-center justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />
                    Min. Qualifying Marks
                  </span>
                  <span className="font-semibold text-slate-800">{s.min_percentage}% aggregate</span>
                </div>

                <div className="flex items-center justify-between py-1">
                  <span className="text-slate-500 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    Financial Assistance
                  </span>
                  <span className="font-semibold text-emerald-700 text-right">
                    {s.config.stipend_amount}
                  </span>
                </div>
              </div>

              {/* Required Documents Summary */}
              <div className="p-6 space-y-4">
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Required Verifiable Documents ({s.config.required_documents?.length || 0})
                  </div>
                  <ul className="space-y-1.5">
                    {s.config.required_documents?.slice(0, 3).map((doc) => (
                      <li key={doc.id} className="text-xs text-slate-600 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                        <span>{doc.name}</span>
                      </li>
                    ))}
                    {(s.config.required_documents?.length || 0) > 3 && (
                      <li className="text-[11px] text-slate-400 italic pl-3.5">
                        + {(s.config.required_documents?.length || 0) - 3} more supporting certificates
                      </li>
                    )}
                  </ul>
                </div>

                <button
                  onClick={() => onSelectScheme(s.code)}
                  className={`w-full py-2.5 px-4 rounded-lg font-semibold text-xs sm:text-sm transition flex items-center justify-center gap-2 ${
                    isNFST
                      ? 'bg-blue-900 hover:bg-blue-800 text-white shadow-sm'
                      : 'bg-emerald-800 hover:bg-emerald-700 text-white shadow-sm'
                  }`}
                >
                  <span>Apply for {s.code}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
