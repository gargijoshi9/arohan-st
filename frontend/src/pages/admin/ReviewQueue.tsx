import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Application, DashboardSummary } from '../../api/types';
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
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [sortBy, setSortBy] = useState<'confidence_score' | 'created_at'>('confidence_score');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [schemeFilter, setSchemeFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [reportError, setReportError] = useState('');

  useEffect(() => {
    fetchQueue();
    api.getDashboard().then(setDashboard).catch((err: unknown) => {
      setReportError(err instanceof Error ? err.message : 'Dashboard metrics are unavailable.');
    });
  }, [sortBy, order, statusFilter, schemeFilter, searchQuery, page]);

  const handleReportDownload = async () => {
    setReportError('');
    try {
      await api.downloadReport();
    } catch (err: unknown) {
      setReportError(err instanceof Error ? err.message : 'Report download failed.');
    }
  };

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      // Searching happens on the server so pagination stays correct.
      const data = await api.getAdminQueue({
        sort_by: sortBy,
        order,
        status: statusFilter,
        scheme_code: schemeFilter,
        search: searchQuery.trim() || undefined,
        page,
        page_size: 25
      });
      setApplications(data.items);
      setTotalPages(Math.max(data.total_pages, 1));
      setTotal(data.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load verification queue');
    } finally {
      setLoading(false);
    }
  };

  // Any filter change returns to the first page.
  const resetToFirstPage = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setPage(1);
  };

  // Calculate quick metrics
  const totalCount = applications.length;

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
            Applications checked against configured rules. The heuristic rule indicator prioritizes review; it is not OCR confidence or an award decision.
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
          <div className="text-[11px] font-semibold text-slate-500 uppercase">Total Applications</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{dashboard?.total_applications ?? total}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Across all configured schemes</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/20 shadow-sm">
          <div className="text-[11px] font-semibold text-rose-700 uppercase flex items-center justify-between">
            <span>Deficiency Actions</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="text-2xl font-bold text-rose-700 mt-1">{dashboard?.by_status.DEFICIENT ?? 0}</div>
          <div className="text-[11px] text-rose-600 mt-0.5">Applicant action requested</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-sm">
          <div className="text-[11px] font-semibold text-emerald-700 uppercase flex items-center justify-between">
            <span>Pending Review</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 mt-1">{(dashboard?.by_status.SUBMITTED ?? 0) + (dashboard?.by_status.UNDER_REVIEW ?? 0)}</div>
          <div className="text-[11px] text-emerald-600 mt-0.5">Manual verification is required</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-[11px] font-semibold text-slate-500 uppercase">Active Awards</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{dashboard?.active_awards ?? 0}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">{dashboard?.pending_payments ?? 0} payment records pending</div>
        </div>
      </div>

      <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div><h3 className="font-bold text-sm text-slate-900">Scheme performance summary</h3><p className="text-[11px] text-slate-500">Aggregated workflow counts for operational monitoring.</p></div>
          <button onClick={() => void handleReportDownload()} className="px-3 py-2 rounded-lg border border-blue-200 text-blue-900 text-xs font-semibold hover:bg-blue-50">Download CSV report</button>
        </div>
        {reportError && <p role="alert" className="text-xs text-rose-700 mb-2">{reportError}</p>}
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-2">
          {Object.entries(dashboard?.by_scheme || {}).map(([code, counts]) => (
            <div key={code} className="rounded-lg bg-slate-50 border p-3 text-xs">
              <div className="font-bold text-blue-950">{code}</div>
              <div className="mt-1 text-slate-600">{counts.total} applications</div>
              <div className="text-slate-500">{counts.approved} approved · {counts.deficient} deficient · {counts.under_review} pending</div>
            </div>
          ))}
          {!dashboard && <p className="text-xs text-slate-500">Loading dashboard metrics…</p>}
        </div>
      </section>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        {/* Search */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by name or app no..."
            value={searchQuery}
            onChange={(e) => resetToFirstPage(setSearchQuery)(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-xs"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Scheme Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-medium">Scheme:</span>
            <select
              value={schemeFilter}
              onChange={(e) => resetToFirstPage(setSchemeFilter)(e.target.value)}
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
              onChange={(e) => resetToFirstPage(setStatusFilter)(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="ALL">All Statuses</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="APPROVED">Approved</option>
              <option value="SELECTED">Selected — Pending Approval</option>
              <option value="NOT_SELECTED">Not Selected</option>
              <option value="DEFICIENT">Deficient</option>
              <option value="REJECTED">Rejected</option>
              <option value="WITHDRAWN">Withdrawn by Applicant</option>
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
        ) : applications.length === 0 ? (
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
                  <th className="py-3 px-4">Rule-check Indicator</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Submitted On</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {applications.map((app) => {
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

        {/* Pagination */}
        {!loading && !error && total > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-slate-200 bg-slate-50 text-xs text-slate-600">
            <span>
              Showing page <span className="font-semibold text-slate-800">{page}</span> of{' '}
              <span className="font-semibold text-slate-800">{totalPages}</span> · {total} application
              {total === 1 ? '' : 's'} match the current filters
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-700 font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 transition"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-700 font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 transition"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
