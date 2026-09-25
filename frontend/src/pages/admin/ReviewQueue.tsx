import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Application } from '../../api/types';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfidenceMeter } from '../../components/ConfidenceMeter';
import { 
  ShieldAlert, 
  Search, 
  Filter, 
  ArrowUpDown, 
  Eye, 
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FileText
} from 'lucide-react';

interface ReviewQueueProps {
  onSelectApplication: (appId: number) => void;
}

export const ReviewQueue: React.FC<ReviewQueueProps> = ({ onSelectApplication }) => {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [sortBy, setSortBy] = useState<'confidence_score' | 'created_at'>('confidence_score');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [schemeFilter, setSchemeFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    fetchQueue();
  }, [sortBy, order, statusFilter, schemeFilter]);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAdminQueue({
        sort_by: sortBy,
        order: order,
        status: statusFilter,
        scheme_code: schemeFilter
      });
      setApplications(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load verification queue');
    } finally {
      setLoading(false);
    }
  };

  const filteredApplications = applications.filter((app) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      app.application_no.toLowerCase().includes(q) ||
      app.applicant_name.toLowerCase().includes(q) ||
      app.applicant_email.toLowerCase().includes(q)
    );
  });

  // Calculate quick metrics
  const totalCount = applications.length;
  const flaggedCount = applications.filter((a) => a.confidence_score < 60).length;
  const highConfidenceCount = applications.filter((a) => a.confidence_score >= 80).length;
  const approvedCount = applications.filter((a) => a.status === 'APPROVED').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-900 border border-emerald-300 uppercase">
              MoTA Officer Adjudication Queue
            </span>
            <span className="text-xs text-slate-500">Autonomous Rule Checking Active</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mt-1">
            Fellowship Verification & Review Desk
          </h2>
          <p className="text-xs text-slate-600 mt-0.5">
            Applications pre-screened by AI rule engine. Sorted by confidence score to prioritize discrepancies or fast-track.
          </p>
        </div>

        <button
          onClick={fetchQueue}
          className="self-start md:self-auto flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-[11px] font-semibold text-slate-500 uppercase">Total in Queue</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Active scheme submissions</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/20 shadow-sm">
          <div className="text-[11px] font-semibold text-rose-700 uppercase flex items-center justify-between">
            <span>Flagged by Rules</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="text-2xl font-bold text-rose-700 mt-1">{flaggedCount}</div>
          <div className="text-[11px] text-rose-600 mt-0.5">Score &lt; 60% (Action Needed)</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-sm">
          <div className="text-[11px] font-semibold text-emerald-700 uppercase flex items-center justify-between">
            <span>High Confidence</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 mt-1">{highConfidenceCount}</div>
          <div className="text-[11px] text-emerald-600 mt-0.5">Score &ge; 80% (Fast-track eligible)</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-[11px] font-semibold text-slate-500 uppercase">Approved Awards</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{approvedCount}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Officially ratified by MoTA</div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        {/* Search */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by name or app no..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-xs"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Scheme Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Scheme:</span>
            <select
              value={schemeFilter}
              onChange={(e) => setSchemeFilter(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="ALL">All Schemes</option>
              <option value="NFST">NFST (National Fellowship)</option>
              <option value="NOS">NOS (Overseas Scholarship)</option>
              <option value="TOP_CLASS">Top Class Education</option>
              <option value="POST_MATRIC">Post-Matric Scholarship</option>
              <option value="PRE_MATRIC">Pre-Matric Scholarship</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="ALL">All Statuses</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="APPROVED">Approved</option>
              <option value="DEFICIENT">Deficient</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          {/* Sort Order */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Order:</span>
            <button
              onClick={() => setOrder(order === 'desc' ? 'asc' : 'desc')}
              className="flex items-center gap-1 px-2.5 py-1.5 border border-slate-300 rounded-lg bg-slate-50 hover:bg-slate-100 font-medium"
              title="Toggle sorting direction"
            >
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-500" />
              <span>{order === 'desc' ? 'Highest Score First' : 'Lowest Score (Flagged First)'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Queue Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-emerald-700 border-r-transparent mb-3" />
            <p className="text-xs text-slate-600">Loading adjudication queue...</p>
          </div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-rose-700">{error}</div>
        ) : filteredApplications.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No applications match the current filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Application No</th>
                  <th className="py-3 px-4">Applicant</th>
                  <th className="py-3 px-4">Scheme</th>
                  <th className="py-3 px-4">AI Confidence Score</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Submitted On</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredApplications.map((app) => {
                  const isFlagged = app.confidence_score < 60;
                  return (
                    <tr
                      key={app.id}
                      className={`hover:bg-slate-50/80 transition ${
                        isFlagged ? 'bg-rose-50/20' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 font-mono font-semibold text-slate-800">
                        {app.application_no}
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900">{app.applicant_name}</div>
                        <div className="text-[11px] text-slate-500">{app.applicant_email}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                          {app.scheme_code}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 w-44">
                        <ConfidenceMeter score={app.confidence_score} size="sm" />
                      </td>

                      <td className="py-3.5 px-4">
                        <StatusBadge status={app.status} size="sm" />
                      </td>

                      <td className="py-3.5 px-4 text-slate-500">
                        {new Date(app.created_at).toLocaleDateString()}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => onSelectApplication(app.id)}
                          className="px-3 py-1.5 rounded-lg bg-blue-900 hover:bg-blue-800 text-white font-semibold transition text-xs flex items-center gap-1.5 ml-auto"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Review</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
