import React, { useState, useEffect } from 'react';
import { api, documentUrl } from '../../api/client';
import { Application, Scheme } from '../../api/types';
import { useAuth } from '../../hooks/useAuth';
import { StatusBadge } from '../../components/StatusBadge';
import { ConfidenceMeter } from '../../components/ConfidenceMeter';
import { 
  Search, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  FileText, 
  Calendar, 
  User, 
  Upload,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface StatusTrackerProps {
  highlightAppId?: number;
  onApplyNew: () => void;
}

export const StatusTracker: React.FC<StatusTrackerProps> = ({ highlightAppId, onApplyNew }) => {
  const { user } = useAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [searchEmail, setSearchEmail] = useState<string>(user?.email || '');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(highlightAppId || null);
  const [schemeConfigs, setSchemeConfigs] = useState<Record<string, Scheme>>({});
  const [uploadingDocument, setUploadingDocument] = useState<string | null>(null);
  const [documentErrors, setDocumentErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (user?.email) {
      setSearchEmail(user.email);
      fetchApplications(user.email);
    }
  }, [user]);

  useEffect(() => {
    if (highlightAppId) {
      setExpandedId(highlightAppId);
    }
  }, [highlightAppId]);

  useEffect(() => {
    const schemeCodes = [...new Set(applications.map((app) => app.scheme_code))];
    if (schemeCodes.length === 0) return;

    Promise.all(schemeCodes.map((code) => api.getSchemeByCode(code)))
      .then((schemes) => {
        setSchemeConfigs(Object.fromEntries(schemes.map((scheme) => [scheme.code, scheme])));
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to load scheme document requirements.');
      });
  }, [applications]);

  const fetchApplications = async (emailToFetch: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getApplicationsByEmail(emailToFetch);
      setApplications(data);
      if (data.length > 0 && !expandedId) {
        setExpandedId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch application status');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchEmail.trim()) {
      fetchApplications(searchEmail.trim());
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const handleDocumentResubmission = async (
    applicationId: number,
    docType: string,
    file: File
  ) => {
    const key = `${applicationId}:${docType}`;
    setUploadingDocument(key);
    setDocumentErrors((previous) => ({ ...previous, [key]: '' }));
    try {
      await api.uploadApplicationDocument(applicationId, docType, file);
      const refreshed = await api.getApplication(applicationId);
      setApplications((previous) => previous.map((app) => app.id === applicationId ? refreshed : app));
    } catch (err: unknown) {
      setDocumentErrors((previous) => ({
        ...previous,
        [key]: err instanceof Error ? err.message : 'Document upload failed.'
      }));
    } finally {
      setUploadingDocument(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Header & Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900">Application Status & AI Audit Tracker</h2>
          <p className="text-xs text-slate-600 mt-1">
            Real-time adjudication timeline for MoTA Scheduled Tribe scholarship & fellowship schemes.
          </p>
        </div>

        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 max-w-sm w-full">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="email"
              value={searchEmail}
              onChange={(e) => setSearchEmail(e.target.value)}
              placeholder="Search by registered email..."
              className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-2 bg-blue-900 text-white rounded-lg text-xs font-semibold hover:bg-blue-800 transition"
          >
            Track
          </button>
        </form>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-900 border-r-transparent mb-3" />
          <p className="text-xs text-slate-600">Retrieving application history and rule records...</p>
        </div>
      ) : error ? (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs mb-6">
          <strong>Error:</strong> {error}
        </div>
      ) : applications.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center max-w-md mx-auto">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No Applications Found</h3>
          <p className="text-xs text-slate-500 mt-1 mb-4">
            No active fellowship or scholarship submissions found for <code>{searchEmail}</code>.
          </p>
          <button
            onClick={onApplyNew}
            className="px-4 py-2 bg-blue-900 text-white rounded-lg text-xs font-semibold hover:bg-blue-800 transition"
          >
            Submit New Application
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {applications.map((app) => {
            const isExpanded = expandedId === app.id;
            const evalData = app.ai_evaluation;
            const hasDiscrepancies = (evalData?.mismatches?.length || 0) > 0;

            return (
              <div
                key={app.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition"
              >
                {/* Application Header Card */}
                <div
                  onClick={() => toggleExpand(app.id)}
                  className="p-5 cursor-pointer hover:bg-slate-50/70 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-300">
                        {app.application_no}
                      </span>
                      <StatusBadge status={app.status} size="sm" />
                      <span className="text-xs text-slate-500">
                        Scheme: <strong className="text-slate-700">{app.scheme_code}</strong>
                      </span>
                    </div>
                    <div className="text-sm font-semibold text-slate-900">{app.scheme_name}</div>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        {app.applicant_name}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {new Date(app.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 self-end md:self-auto">
                    <div className="w-36 text-right">
                      <ConfidenceMeter score={app.confidence_score} size="sm" />
                    </div>
                    <div className="text-slate-400">
                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </div>
                  </div>
                </div>

                {/* Expanded Timeline & Details */}
                {isExpanded && (
                  <div className="p-5 bg-slate-50/50 space-y-6">
                    {/* Stage Timeline */}
                    <div className="bg-white p-4 rounded-xl border border-slate-200">
                      <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">
                        Adjudication Stage Timeline
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Step 1 */}
                        <div className="flex items-start gap-3 p-3 rounded-lg bg-emerald-50/70 border border-emerald-200">
                          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs font-bold text-emerald-900">1. Submission Received</div>
                            <div className="text-[11px] text-emerald-700 mt-0.5">
                              Registered on {new Date(app.created_at).toLocaleDateString()}
                            </div>
                          </div>
                        </div>

                        {/* Step 2 */}
                        <div
                          className={`flex items-start gap-3 p-3 rounded-lg border ${
                            app.confidence_score >= 80
                              ? 'bg-emerald-50/70 border-emerald-200'
                              : 'bg-amber-50/70 border-amber-200'
                          }`}
                        >
                          {app.confidence_score >= 80 ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                          )}
                          <div>
                            <div
                              className={`text-xs font-bold ${
                                app.confidence_score >= 80 ? 'text-emerald-900' : 'text-amber-900'
                              }`}
                            >
                              2. Configured Rule Checks
                            </div>
                            <div className="text-[11px] text-slate-600 mt-0.5">
                              Rule indicator: <strong>{app.confidence_score}%</strong> (
                              {evalData?.passed_checks?.length || 0} checks passed)
                            </div>
                          </div>
                        </div>

                        {/* Step 3 */}
                        <div
                          className={`flex items-start gap-3 p-3 rounded-lg border ${
                            app.status === 'APPROVED'
                              ? 'bg-emerald-50/70 border-emerald-200'
                              : app.status === 'DEFICIENT'
                              ? 'bg-rose-50/70 border-rose-200'
                              : 'bg-blue-50/70 border-blue-200'
                          }`}
                        >
                          {app.status === 'APPROVED' ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          ) : app.status === 'DEFICIENT' ? (
                            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                          ) : (
                            <Clock className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                          )}
                          <div>
                            <div className="text-xs font-bold text-slate-900">3. MoTA Officer Desk</div>
                            <div className="text-[11px] text-slate-600 mt-0.5">
                              Current Status: <StatusBadge status={app.status} size="sm" />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Deficient Alert Banner */}
                    {app.status === 'DEFICIENT' && (
                      <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-xs text-rose-900 space-y-2">
                        <div className="flex items-center gap-2 font-bold text-rose-800">
                          <AlertTriangle className="w-4 h-4 text-rose-600" />
                          <span>Application Marked as Deficient — Applicant Action Required</span>
                        </div>
                        {app.admin_remarks && (
                          <div className="bg-white/80 p-2.5 rounded border border-rose-200">
                            <strong>Officer Note:</strong> {app.admin_remarks}
                          </div>
                        )}
                        <p className="text-[11px] text-rose-700">
                          Review the reported issues below and upload a clearer or corrected document where requested. Extracted values are preliminary and do not authenticate documents.
                        </p>
                      </div>
                    )}

                    {/* AI Rule Engine Evaluation Report */}
                    {evalData && (
                      <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-3">
                        <div className="flex items-center justify-between border-b pb-2">
                          <div className="text-xs font-bold text-slate-800">Configured Eligibility Rule Report</div>
                          <div className="text-xs text-slate-500">
                            Rule indicator: <span className="font-bold text-slate-800">{evalData.confidence_score}%</span>
                          </div>
                        </div>

                        <p className="text-xs text-slate-600">{evalData.summary}</p>

                        {/* Mismatches in RED if any */}
                        {hasDiscrepancies && (
                          <div className="space-y-2 pt-1">
                            <div className="text-xs font-bold text-rose-700">Identified Discrepancies:</div>
                            {evalData.mismatches.map((m, idx) => (
                              <div
                                key={idx}
                                className="p-2.5 bg-rose-50/80 border border-rose-200 rounded-lg text-xs space-y-1"
                              >
                                <div className="flex items-center justify-between font-semibold text-rose-900">
                                  <span>{m.label} ({m.field})</span>
                                  <span className="text-[10px] uppercase px-1.5 py-0.2 bg-rose-200 text-rose-800 rounded font-bold">
                                    {m.severity}
                                  </span>
                                </div>
                                <div className="text-slate-700">
                                  Declared: <span className="font-mono text-rose-700 font-bold">{m.declared_value}</span>
                                  {' | '}
                                  Rule: <span className="text-slate-600">{m.expected_rule}</span>
                                </div>
                                <div className="text-[11px] text-rose-800">{m.description}</div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Passed Checks */}
                        {evalData.passed_checks?.length > 0 && (
                          <div className="pt-2">
                            <div className="text-xs font-semibold text-emerald-800 mb-1.5">
                              Checks With No Rule Mismatch:
                            </div>
                            <ul className="space-y-1">
                              {evalData.passed_checks.map((chk, i) => (
                                <li key={i} className="text-xs text-slate-600 flex items-center gap-1.5">
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                                  <span>{chk}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Declared Fields Snapshot */}
                    <div className="bg-white p-4 rounded-xl border border-slate-200">
                      <div className="text-xs font-bold text-slate-800 border-b pb-2 mb-3">
                        Submitted Application Summary
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                        {Object.entries(app.declared_data).map(([key, val]) => (
                          <div key={key} className="bg-slate-50 p-2 rounded border border-slate-200/70">
                            <span className="text-slate-400 text-[10px] block uppercase font-semibold">
                              {key.replace(/_/g, ' ')}
                            </span>
                            <span className="font-medium text-slate-800 break-words">{String(val)}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Documents List */}
                    {(app.documents?.length > 0 || schemeConfigs[app.scheme_code]) && (
                      <div className="bg-white p-4 rounded-xl border border-slate-200">
                        <div className="text-xs font-bold text-slate-800 border-b pb-2 mb-2">
                          Documents and OCR Extraction (Not Document Authentication)
                        </div>
                        <div className="space-y-3">
                          {(schemeConfigs[app.scheme_code]?.config.required_documents || app.documents.map((doc) => ({
                            id: doc.doc_type,
                            name: doc.doc_type.replace(/_/g, ' '),
                            required: true,
                            description: ''
                          }))).map((requiredDoc) => {
                            const doc = app.documents.find((item) => item.doc_type === requiredDoc.id);
                            const key = `${app.id}:${requiredDoc.id}`;
                            const canResubmit = app.status !== 'APPROVED' && app.status !== 'REJECTED'
                              && (!doc || doc.ocr_status !== 'SUCCESS' || app.status === 'DEFICIENT');
                            return (
                              <div key={requiredDoc.id} className="p-3 rounded-lg border border-slate-200">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                  <div className="flex items-center gap-2">
                                    <FileText className="w-3.5 h-3.5 text-blue-700" />
                                    <span className="font-medium text-slate-800 text-xs">{requiredDoc.name}</span>
                                    {requiredDoc.required && <span className="text-[10px] text-slate-500">Required</span>}
                                  </div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    {doc && <span className="text-[11px] text-slate-600">{doc.file_name}</span>}
                                    <span className={`text-[11px] px-2 py-0.5 rounded font-medium ${
                                      doc?.ocr_status === 'SUCCESS'
                                        ? 'bg-emerald-50 text-emerald-700'
                                        : 'bg-amber-50 text-amber-800'
                                    }`}>{doc?.ocr_status === 'SUCCESS' ? 'FIELDS EXTRACTED' : doc?.ocr_status || 'NOT UPLOADED'}</span>
                                    {doc?.file_path?.startsWith('/uploads/') && (
                                      <a href={documentUrl(doc.file_path)} target="_blank" rel="noreferrer" className="text-xs font-semibold text-blue-800 underline">View</a>
                                    )}
                                  </div>
                                </div>
                                {doc?.extraction_method && (
                                  <div className="mt-1 text-[10px] text-slate-500">
                                    Extracted with {doc.extraction_method}
                                    {doc.ocr_confidence != null && ` · Tesseract confidence ${Math.round(doc.ocr_confidence * 100)}%`}
                                  </div>
                                )}
                                {doc?.parsed_fields && Object.keys(doc.parsed_fields).length > 0 && (
                                  <div className="mt-2 flex flex-wrap gap-2">
                                    {Object.entries(doc.parsed_fields).map(([field, value]) => (
                                      <span key={field} className="text-[10px] bg-blue-50 text-blue-900 px-2 py-1 rounded">
                                        {field.replace(/_/g, ' ')}: {String(value)}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                {doc?.failed_reason && <p className="mt-2 text-[11px] text-rose-700">{doc.failed_reason}</p>}
                                {canResubmit && (
                                  <label className="mt-2 inline-flex cursor-pointer items-center gap-1.5 rounded border border-slate-300 px-2.5 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
                                    <Upload className="w-3.5 h-3.5" />
                                    {uploadingDocument === key ? 'Processing…' : doc ? 'Replace and re-run OCR' : 'Upload required document'}
                                    <input
                                      type="file"
                                      accept=".pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.txt"
                                      className="hidden"
                                      disabled={uploadingDocument === key}
                                      onChange={(event) => {
                                        const file = event.target.files?.[0];
                                        if (file) void handleDocumentResubmission(app.id, requiredDoc.id, file);
                                        event.target.value = '';
                                      }}
                                    />
                                  </label>
                                )}
                                {documentErrors[key] && <p className="mt-1 text-[11px] text-rose-700">{documentErrors[key]}</p>}
                                {doc?.extracted_text && (
                                  <details className="mt-2">
                                    <summary className="cursor-pointer text-[10px] font-medium text-slate-600">View extracted text</summary>
                                    <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[10px] text-slate-700">{doc.extracted_text}</pre>
                                  </details>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
