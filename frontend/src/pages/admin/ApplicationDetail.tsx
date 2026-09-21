import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Application } from '../../api/types';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfidenceMeter } from '../../components/ConfidenceMeter';
import { 
  ArrowLeft, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  FileText, 
  ShieldCheck, 
  User, 
  Calendar,
  Send,
  AlertCircle
} from 'lucide-react';

interface ApplicationDetailProps {
  applicationId: number;
  onBackToQueue: () => void;
}

export const ApplicationDetail: React.FC<ApplicationDetailProps> = ({
  applicationId,
  onBackToQueue
}) => {
  const [app, setApp] = useState<Application | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [updating, setUpdating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [remarks, setRemarks] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadApplication();
  }, [applicationId]);

  const loadApplication = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getApplication(applicationId);
      setApp(data);
      setRemarks(data.admin_remarks || '');
    } catch (err: any) {
      setError(err.message || 'Failed to load application details');
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (decision: 'APPROVE' | 'REJECT' | 'DEFICIENT') => {
    if (!app) return;
    setUpdating(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const updated = await api.submitAdminDecision(app.id, {
        decision,
        remarks: remarks.trim()
      });
      setApp(updated);
      setSuccessMsg(`Application status updated to ${updated.status} successfully.`);
    } catch (err: any) {
      setError(err.message || 'Failed to record decision');
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-900 border-r-transparent mb-3" />
        <p className="text-xs text-slate-600">Loading application details and rule engine trace...</p>
      </div>
    );
  }

  if (error || !app) {
    return (
      <div className="max-w-xl mx-auto my-8 p-6 bg-white rounded-lg border border-slate-200 text-center">
        <p className="text-xs text-rose-700">{error || 'Application not found'}</p>
        <button
          onClick={onBackToQueue}
          className="mt-4 px-4 py-2 bg-blue-900 text-white rounded text-xs"
        >
          Return to Queue
        </button>
      </div>
    );
  }

  const evalData = app.ai_evaluation;
  const mismatches = evalData?.mismatches || [];
  const hasErrors = mismatches.some((m) => m.severity === 'ERROR');

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header & Back Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <button
          onClick={onBackToQueue}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-blue-900 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Verification Queue</span>
        </button>

        <div className="flex items-center gap-2.5">
          <span className="font-mono text-xs font-bold px-3 py-1 rounded bg-slate-200 text-slate-800">
            {app.application_no}
          </span>
          <StatusBadge status={app.status} size="md" />
        </div>
      </div>

      {successMsg && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-xl text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* AI Rule Verification Highlight Panel */}
      <div
        className={`p-5 rounded-xl border ${
          hasErrors
            ? 'bg-rose-50 border-rose-300 shadow-sm'
            : 'bg-emerald-50 border-emerald-300 shadow-sm'
        }`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-black/10">
          <div className="flex items-center gap-2.5">
            <div
              className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                hasErrors ? 'bg-rose-600 text-white' : 'bg-emerald-600 text-white'
              }`}
            >
              {hasErrors ? <AlertTriangle className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
            </div>
            <div>
              <div
                className={`text-sm font-bold ${
                  hasErrors ? 'text-rose-900' : 'text-emerald-900'
                }`}
              >
                {hasErrors
                  ? 'AI Rule Engine: Discrepancies Flagged'
                  : 'AI Rule Engine: Statutory Compliance Passed'}
              </div>
              <div className="text-[11px] text-slate-600">{evalData?.summary}</div>
            </div>
          </div>

          <div className="w-48 self-end md:self-auto">
            <ConfidenceMeter score={app.confidence_score} size="md" />
          </div>
        </div>

        {/* Mismatches List Highlighted in RED */}
        {mismatches.length > 0 && (
          <div className="pt-4 space-y-2.5">
            <div className="text-xs font-bold text-rose-900 uppercase tracking-wider">
              Rule Discrepancies Detected ({mismatches.length}):
            </div>
            {mismatches.map((m, idx) => (
              <div
                key={idx}
                className="p-3 bg-white rounded-lg border-l-4 border-l-rose-600 border border-rose-200 shadow-xs space-y-1"
              >
                <div className="flex items-center justify-between text-xs font-bold text-rose-900">
                  <span>{m.label} ({m.field})</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-rose-100 text-rose-800 uppercase tracking-wider">
                    {m.severity}
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs py-1">
                  <div className="bg-rose-50/60 p-2 rounded border border-rose-100">
                    <span className="text-slate-500 text-[10px] block uppercase font-medium">Applicant Declared:</span>
                    <span className="font-bold text-rose-700">{String(m.declared_value)}</span>
                  </div>
                  <div className="bg-slate-50 p-2 rounded border border-slate-200">
                    <span className="text-slate-500 text-[10px] block uppercase font-medium">Statutory MoTA Cap:</span>
                    <span className="font-semibold text-slate-800">{m.expected_rule}</span>
                  </div>
                </div>
                <p className="text-[11px] text-rose-700 italic">{m.description}</p>
              </div>
            ))}
          </div>
        )}

        {/* Passed checks */}
        {evalData?.passed_checks && evalData.passed_checks.length > 0 && (
          <div className="pt-3">
            <div className="text-[11px] font-bold text-emerald-900 uppercase tracking-wider mb-1.5">
              Verified Compliant Rules ({evalData.passed_checks.length}):
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {evalData.passed_checks.map((chk, i) => (
                <div key={i} className="text-xs text-emerald-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                  <span>{chk}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Main Content Grid: Details vs Adjudication Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Applicant Declared Fields & Documents */}
        <div className="lg:col-span-2 space-y-6">
          {/* Scheme & Applicant Info */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <span className="text-xs font-bold text-blue-900 px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
                  {app.scheme_code}
                </span>
                <h3 className="text-base font-bold text-slate-900 mt-1">{app.scheme_name}</h3>
              </div>
              <div className="text-right text-xs text-slate-500">
                <div>Submitted: {new Date(app.created_at).toLocaleDateString()}</div>
                <div>Last Updated: {new Date(app.updated_at).toLocaleDateString()}</div>
              </div>
            </div>

            {/* Applicant Profile */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-400 text-[10px] uppercase block font-semibold">Applicant Name</span>
                <span className="font-bold text-slate-900">{app.applicant_name}</span>
              </div>

              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-400 text-[10px] uppercase block font-semibold">Email</span>
                <span className="font-medium text-slate-800 truncate block">{app.applicant_email}</span>
              </div>

              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-400 text-[10px] uppercase block font-semibold">Social Category</span>
                <span className="font-bold text-blue-900">{app.declared_data?.category || 'ST'}</span>
              </div>
            </div>
          </div>

          {/* Declared Fields Breakdown */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-900" />
              <span>Applicant Declared Parameters</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {Object.entries(app.declared_data).map(([k, v]) => {
                const isMismatchField = mismatches.some((m) => m.field === k);
                return (
                  <div
                    key={k}
                    className={`p-2.5 rounded-lg border transition ${
                      isMismatchField
                        ? 'bg-rose-50/80 border-rose-300 ring-1 ring-rose-200'
                        : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <span className="text-slate-400 text-[10px] uppercase block font-semibold">
                      {k.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={`font-semibold break-words ${
                        isMismatchField ? 'text-rose-800 font-bold' : 'text-slate-800'
                      }`}
                    >
                      {String(v)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Uploaded Documents List */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">
              Attached Statutory Verification Documents ({app.documents?.length || 0})
            </h4>

            {app.documents?.length === 0 ? (
              <p className="text-xs text-slate-500">No documents attached.</p>
            ) : (
              <div className="divide-y divide-slate-100 text-xs">
                {app.documents.map((d) => (
                  <div key={d.id} className="py-2.5 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <FileText className="w-4 h-4 text-blue-800" />
                      <div>
                        <div className="font-semibold text-slate-800">{d.file_name}</div>
                        <div className="text-[11px] text-slate-500">Type: {d.doc_type}</div>
                      </div>
                    </div>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Verified Reference
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Officer Adjudication Decision Panel */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm sticky top-20">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 pb-2 border-b">
              Officer Adjudication Desk
            </h4>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-500 font-semibold mb-1">Current Application Status</label>
                <StatusBadge status={app.status} size="lg" />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1.5">
                  Official Decision Remarks / Defect Note
                </label>
                <textarea
                  rows={4}
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="Enter reason for approval, rejection, or specific rectification instructions for the scholar..."
                  className="w-full p-2.5 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>

              {/* Action Buttons */}
              <div className="pt-2 space-y-2">
                <button
                  type="button"
                  disabled={updating}
                  onClick={() => handleDecision('APPROVE')}
                  className="w-full py-2.5 px-3 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:bg-slate-300 text-white font-bold transition flex items-center justify-center gap-2 shadow-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Approve Fellowship Award</span>
                </button>

                <button
                  type="button"
                  disabled={updating}
                  onClick={() => handleDecision('DEFICIENT')}
                  className="w-full py-2.5 px-3 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:bg-slate-300 text-white font-bold transition flex items-center justify-center gap-2 shadow-sm"
                >
                  <AlertTriangle className="w-4 h-4" />
                  <span>Request Resubmission (Deficient)</span>
                </button>

                <button
                  type="button"
                  disabled={updating}
                  onClick={() => handleDecision('REJECT')}
                  className="w-full py-2.5 px-3 rounded-lg bg-rose-700 hover:bg-rose-600 disabled:bg-slate-300 text-white font-bold transition flex items-center justify-center gap-2 shadow-sm"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Reject Application</span>
                </button>
              </div>

              <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 space-y-1">
                <p>• <strong>Approve</strong>: Finalizes grant of fellowship stipend.</p>
                <p>• <strong>Request Resubmission</strong>: Notifies candidate to remedy discrepancy.</p>
                <p>• <strong>Reject</strong>: Disqualifies application per statutory guidelines.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
