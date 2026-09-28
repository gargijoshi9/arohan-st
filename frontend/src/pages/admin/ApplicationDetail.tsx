import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Application, Scheme } from '../../api/types';
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
  const [audit, setAudit] = useState<Array<{ id: number; actor_email: string; actor_role: string; action: string; from_status?: string; to_status?: string; remarks?: string; created_at: string }>>([]);
  const [docAction, setDocAction] = useState<{ docId: number; decision: 'VERIFY' | 'DEFICIENT' } | null>(null);
  const [docRemarks, setDocRemarks] = useState('');
  const [docBusy, setDocBusy] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);
  const [schemeConfig, setSchemeConfig] = useState<Scheme | null>(null);

  useEffect(() => {
    loadApplication();
  }, [applicationId]);

  const refresh = async () => {
    const [data, history] = await Promise.all([
      api.getApplication(applicationId),
      api.getApplicationAudit(applicationId)
    ]);
    setApp(data);
    setAudit(history);
    return data;
  };

  const loadApplication = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await refresh();
      setRemarks(data.admin_remarks || '');
      api.getSchemeByCode(data.scheme_code).then(setSchemeConfig).catch(() => setSchemeConfig(null));
    } catch (err: any) {
      setError(err.message || 'Failed to load application details');
    } finally {
      setLoading(false);
    }
  };

  const startDocAction = (docId: number, decision: 'VERIFY' | 'DEFICIENT') => {
    setDocAction({ docId, decision });
    setDocRemarks('');
    setDocError(null);
  };

  const submitDocAction = async () => {
    if (!docAction) return;
    setDocBusy(true);
    setDocError(null);
    const decisionRemarks = remarks;
    try {
      await api.verifyDocument(docAction.docId, { decision: docAction.decision, remarks: docRemarks.trim() });
      await refresh();
      setRemarks(decisionRemarks);
      setDocAction(null);
      setDocRemarks('');
      setSuccessMsg(`Document ${docAction.decision === 'VERIFY' ? 'verified' : 'marked deficient'}.`);
    } catch (err: any) {
      setDocError(err.message || 'Failed to record the document review.');
    } finally {
      setDocBusy(false);
    }
  };

  const handleDecision = async (decision: 'APPROVE' | 'REJECT' | 'DEFICIENT' | 'SELECT' | 'NOT_SELECT') => {
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
      setAudit(await api.getApplicationAudit(app.id));
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

  const requiredDocIds = (schemeConfig?.config.required_documents || [])
    .filter((doc) => doc.required)
    .map((doc) => doc.id);
  const verifiedDocIds = (app.documents || [])
    .filter((doc) => doc.status === 'VERIFIED')
    .map((doc) => doc.doc_type);
  const unverifiedRequired = requiredDocIds.filter((id) => !verifiedDocIds.includes(id));
  const isFinalStatus = ['APPROVED', 'REJECTED'].includes(app.status);
  const selectionReady = evalData?.pass_fail === true && unverifiedRequired.length === 0;
  const canReviewDocuments = !isFinalStatus && app.documents.length > 0;

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
                  : 'No Configured Rule Mismatch — Officer Verification Still Required'}
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
              Checks With No Rule Mismatch ({evalData.passed_checks.length}):
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
              Uploaded Documents — OCR Does Not Authenticate Documents ({app.documents?.length || 0})
            </h4>

            {app.documents?.length === 0 ? (
              <p className="text-xs text-slate-500">No documents attached.</p>
            ) : (
              <div className="divide-y divide-slate-100 text-xs">
                {app.documents.map((d) => (
                  <div key={d.id} className="py-2.5 border-b border-slate-100 last:border-b-0">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <FileText className="w-4 h-4 text-blue-800 flex-shrink-0" />
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-800 truncate">{d.file_name}</div>
                          <div className="text-[11px] text-slate-500">Type: {d.doc_type}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0 flex-wrap justify-end">
                        {d.status && (
                          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                            d.status === 'VERIFIED'
                              ? 'bg-blue-50 text-blue-800 border-blue-200'
                              : d.status === 'DEFICIENT'
                              ? 'bg-amber-50 text-amber-800 border-amber-200'
                              : 'bg-slate-50 text-slate-600 border-slate-200'
                          }`}>{d.status === 'VERIFIED' ? 'OFFICER VERIFIED' : d.status}</span>
                        )}
                        <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                          d.ocr_status === 'SUCCESS'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : d.ocr_status === 'PARTIAL'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}>{d.ocr_status === 'SUCCESS' ? 'FIELDS EXTRACTED' : `OCR ${d.ocr_status || 'PENDING'}`}</span>
                        {d.file_path && <button type="button" onClick={() => void api.openDocument(d.file_path!).catch((err: unknown) => setError(err instanceof Error ? err.message : 'Unable to open document.'))} className="text-xs font-semibold text-blue-800 underline">View file</button>}
                        {canReviewDocuments && d.id != null && (
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              disabled={docAction?.docId === d.id && docBusy}
                              onClick={() => startDocAction(d.id!, 'VERIFY')}
                              className="text-[11px] font-semibold px-2 py-1 rounded border border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 disabled:opacity-50"
                            >
                              Verify
                            </button>
                            <button
                              type="button"
                              disabled={docAction?.docId === d.id && docBusy}
                              onClick={() => startDocAction(d.id!, 'DEFICIENT')}
                              className="text-[11px] font-semibold px-2 py-1 rounded border border-amber-300 text-amber-800 bg-amber-50 hover:bg-amber-100 disabled:opacity-50"
                            >
                              Deficient
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                    {canReviewDocuments && d.id != null && docAction?.docId === d.id && (
                      <div className="mt-2 ml-6 rounded-lg border border-slate-300 bg-slate-50 p-3 space-y-2">
                        <p className="text-[11px] text-slate-600">
                          {docAction.decision === 'VERIFY'
                            ? 'Record your verification of this document against the issuing authority.'
                            : 'Explain what is wrong so the applicant can upload an acceptable replacement.'}
                          A written reason is required and is sent to the applicant and the audit log.
                        </p>
                        <textarea
                          rows={2}
                          value={docRemarks}
                          onChange={(e) => setDocRemarks(e.target.value)}
                          placeholder={docAction.decision === 'VERIFY' ? 'e.g. Certificate number matches the State portal record.' : 'e.g. Scan is illegible; please upload a readable certified copy.'}
                          className="w-full p-2 border border-slate-300 rounded-lg text-[11px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        {docError && <p role="alert" className="text-[11px] text-rose-700">{docError}</p>}
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            disabled={docBusy || !docRemarks.trim()}
                            onClick={() => void submitDocAction()}
                            className="text-[11px] font-semibold px-3 py-1.5 rounded bg-blue-900 text-white hover:bg-blue-800 disabled:opacity-40"
                          >
                            {docBusy ? 'Recording…' : 'Confirm decision'}
                          </button>
                          <button
                            type="button"
                            disabled={docBusy}
                            onClick={() => { setDocAction(null); setDocRemarks(''); setDocError(null); }}
                            className="text-[11px] font-semibold px-3 py-1.5 rounded border border-slate-300 text-slate-700 hover:bg-slate-100 disabled:opacity-40"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                    {d.extraction_method && (
                      <div className="mt-1 ml-6 text-[10px] text-slate-500">
                        {d.extraction_method}
                        {d.ocr_confidence != null && ` · OCR confidence ${Math.round(d.ocr_confidence * 100)}%`}
                      </div>
                    )}
                    {d.parsed_fields && Object.keys(d.parsed_fields).length > 0 && (
                      <div className="mt-2 ml-6 flex flex-wrap gap-2">
                        {Object.entries(d.parsed_fields).map(([field, value]) => (
                          <span key={field} className="text-[10px] bg-blue-50 text-blue-900 px-2 py-1 rounded">
                            {field.replace(/_/g, ' ')}: {String(value)}
                          </span>
                        ))}
                      </div>
                    )}
                    {d.failed_reason && <p className="mt-1 ml-6 text-[11px] text-rose-700">{d.failed_reason}</p>}
                    {d.extracted_text && (
                      <details className="mt-2 ml-6">
                        <summary className="cursor-pointer text-[10px] font-medium text-slate-600">View extracted text</summary>
                        <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[10px] text-slate-700">{d.extracted_text}</pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">Workflow audit trail</h4>
            {audit.length === 0 ? <p className="text-xs text-slate-500">No recorded workflow events.</p> : (
              <ol className="space-y-3">
                {audit.map((event) => <li key={event.id} className="border-l-2 border-blue-200 pl-3 text-xs">
                  <div className="font-semibold text-slate-800">{event.action.replace(/_/g, ' ')}</div>
                  <div className="text-slate-500">{event.actor_role} · {event.actor_email} · {new Date(event.created_at).toLocaleString()}</div>
                  {(event.from_status || event.to_status) && <div className="text-slate-600">{event.from_status || 'NEW'} → {event.to_status || '—'}</div>}
                  {event.remarks && <p className="mt-1 text-slate-700">{event.remarks}</p>}
                </li>)}
              </ol>
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

              {!isFinalStatus && schemeConfig && (
                <div className={`rounded-lg border p-3 ${
                  selectionReady ? 'bg-emerald-50 border-emerald-300' : 'bg-amber-50 border-amber-300'
                }`}>
                  <div className={`text-[11px] font-bold ${selectionReady ? 'text-emerald-900' : 'text-amber-900'}`}>
                    Selection readiness: {verifiedDocIds.filter((id) => requiredDocIds.includes(id)).length} of {requiredDocIds.length} required documents officer-verified
                  </div>
                  {!selectionReady && (
                    <ul className="mt-1.5 space-y-0.5 text-[10px] text-amber-900 list-disc pl-4">
                      {unverifiedRequired.length > 0 && (
                        <li>Verify every required document above: {unverifiedRequired.join(', ')}.</li>
                      )}
                      {evalData?.pass_fail !== true && (
                        <li>Configured eligibility checks still report issues; resolve them or request resubmission.</li>
                      )}
                    </ul>
                  )}
                  <p className="mt-1.5 text-[10px] text-slate-600">
                    Recording a merit selection is blocked until both conditions are met.
                  </p>
                </div>
              )}

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
                <p className="mt-1 text-[10px] text-slate-500">A written reason is required for selection, approval, deficiency and rejection; it is included in the applicant notice and audit log.</p>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 space-y-2">
                <button
                  type="button"
                  disabled={updating || !remarks.trim()}
                  onClick={() => handleDecision('APPROVE')}
                  className="w-full py-2.5 px-3 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:bg-slate-300 text-white font-bold transition flex items-center justify-center gap-2 shadow-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Approve and Create Award Record</span>
                </button>

                <button
                  type="button"
                  disabled={updating || !remarks.trim()}
                  onClick={() => handleDecision('SELECT')}
                  className="w-full py-2.5 px-3 rounded-lg bg-indigo-700 hover:bg-indigo-600 disabled:bg-slate-300 text-white font-bold transition flex items-center justify-center gap-2 shadow-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Record Merit Selection</span>
                </button>

                <button
                  type="button"
                  disabled={updating || !remarks.trim()}
                  onClick={() => handleDecision('NOT_SELECT')}
                  className="w-full py-2.5 px-3 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:bg-slate-300 text-white font-bold transition flex items-center justify-center gap-2 shadow-sm"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Record Not Selected</span>
                </button>

                <button
                  type="button"
                  disabled={updating || !remarks.trim()}
                  onClick={() => handleDecision('DEFICIENT')}
                  className="w-full py-2.5 px-3 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:bg-slate-300 text-white font-bold transition flex items-center justify-center gap-2 shadow-sm"
                >
                  <AlertTriangle className="w-4 h-4" />
                  <span>Request Resubmission (Deficient)</span>
                </button>

                <button
                  type="button"
                  disabled={updating || !remarks.trim()}
                  onClick={() => handleDecision('REJECT')}
                  className="w-full py-2.5 px-3 rounded-lg bg-rose-700 hover:bg-rose-600 disabled:bg-slate-300 text-white font-bold transition flex items-center justify-center gap-2 shadow-sm"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Reject Application</span>
                </button>
              </div>

              <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 space-y-1">
                <p>• Selection ranking is advisory; authorized officer decision and rationale are recorded.</p>
                <p>• Approval creates an award record; payment processing is outside this prototype.</p>
                <p>• Notifications appear in the applicant portal; external email/SMS delivery is not configured.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
