import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Scheme } from '../../api/types';
import { useAuth } from '../../hooks/useAuth';
import { 
  FileText, 
  Upload, 
  CheckCircle2, 
  ShieldCheck, 
  ArrowLeft,
  Info
} from 'lucide-react';

interface ApplicationFormProps {
  initialSchemeCode?: string;
  onBackToSchemes: () => void;
  onSubmitSuccess: (applicationId: number) => void;
}

export const ApplicationForm: React.FC<ApplicationFormProps> = ({
  initialSchemeCode = 'NFST',
  onBackToSchemes,
  onSubmitSuccess
}) => {
  const { user } = useAuth();
  const [selectedSchemeCode] = useState<string>(initialSchemeCode);
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [uploadedDocs, setUploadedDocs] = useState<Record<string, {
    file: File;
    uploaded: boolean;
    ocrStatus?: string;
    parsedFields?: Record<string, any> | null;
    failedReason?: string | null;
  }>>({});
  const [applicationId, setApplicationId] = useState<number | null>(null);

  useEffect(() => {
    loadScheme(selectedSchemeCode);
  }, [selectedSchemeCode]);

  const loadScheme = async (code: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSchemeByCode(code);
      setScheme(data);
      
      // Initialize every form from its configured fields; do not infer eligibility values.
      const initial: Record<string, any> = Object.fromEntries(
        data.config.form_fields.map((field) => [field.name, ''])
      );
      initial.full_name = user?.name || '';
      initial.email = user?.email || '';

      setFormData(initial);

      setUploadedDocs({});
    } catch (err: any) {
      setError(err.message || 'Failed to load scheme configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleFileUpload = (docId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const allowedExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.txt'];
    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!allowedExtensions.includes(extension)) {
      setError('Choose a PDF, image, or TXT document.');
      e.target.value = '';
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Each document must be 10 MB or smaller.');
      e.target.value = '';
      return;
    }
    setError(null);
    setUploadedDocs((prev) => ({
      ...prev,
      [docId]: { file, uploaded: false }
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheme) return;

    setSubmitting(true);
    setError(null);
    let targetApplicationId = applicationId;
    try {
      if (targetApplicationId === null) {
        const result = await api.submitApplication({
          scheme_code: scheme.code,
          full_name: formData.full_name || user?.name || 'Applicant',
          email: formData.email || user?.email || 'applicant@example.com',
          phone: formData.phone || '',
          declared_fields: formData,
          documents: []
        });
        targetApplicationId = result.id;
        setApplicationId(result.id);
      }

      const failedUploads: string[] = [];
      for (const [docType, selected] of Object.entries(uploadedDocs)) {
        if (selected.uploaded) continue;
        try {
          const result = await api.uploadApplicationDocument(targetApplicationId, docType, selected.file);
          setUploadedDocs((previous) => ({
            ...previous,
            [docType]: {
              ...previous[docType],
              uploaded: true,
              ocrStatus: result.ocr_status || 'PENDING',
              parsedFields: result.parsed_fields,
              failedReason: result.failed_reason
            }
          }));
        } catch (uploadError) {
          failedUploads.push(selected.file.name);
          setUploadedDocs((previous) => ({
            ...previous,
            [docType]: { ...previous[docType], uploaded: false }
          }));
        }
      }

      if (failedUploads.length) {
        throw new Error(`Application saved, but these uploads need retrying: ${failedUploads.join(', ')}.`);
      }
      onSubmitSuccess(targetApplicationId);
    } catch (err: any) {
      setError(err.message || 'Failed to submit application');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-900 border-r-transparent mb-3" />
        <p className="text-sm text-slate-600">Preparing dynamic scheme application form...</p>
      </div>
    );
  }

  if (!scheme) {
    return (
      <div className="max-w-xl mx-auto my-8 p-6 bg-white rounded-lg border border-slate-200 text-center">
        <p className="text-sm text-slate-600">Scheme not found.</p>
        <button onClick={onBackToSchemes} className="mt-4 px-4 py-2 bg-blue-900 text-white rounded text-xs">
          Return to Schemes
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Top Breadcrumb & Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <button
          onClick={onBackToSchemes}
          className="flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-blue-900 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Schemes Catalog</span>
        </button>

      </div>

      {/* Scheme Banner */}
      <div className="bg-gradient-to-r from-blue-900 to-slate-900 rounded-xl p-6 text-white shadow-md mb-6">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <span className="text-xs font-bold px-2.5 py-0.5 rounded bg-amber-400 text-blue-950">
            {scheme.code} Scheme Application
          </span>
          <span className="text-xs text-blue-200">Department: Ministry of Tribal Affairs</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold">{scheme.name}</h2>
        <p className="text-xs text-blue-100 mt-1 max-w-2xl">{scheme.description}</p>

      </div>

      {error && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
          <strong>Submission Error:</strong> {error}
        </div>
      )}

      {/* Application Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section 1: Declared Fields */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2 border-b pb-2">
            <FileText className="w-4 h-4 text-blue-900" />
            <span>Section 1: Applicant Declared Fields</span>
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            These declarations are checked against configured scheme rules. Document contents and eligibility claims still need officer verification.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {scheme.config.form_fields?.map((field) => (
              <div key={field.name} className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  {field.label} {field.required && <span className="text-rose-500">*</span>}
                </label>

                {field.type === 'select' ? (
                  <select
                    required={field.required}
                    value={formData[field.name] || ''}
                    onChange={(e) => handleInputChange(field.name, e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-600"
                  >
                    <option value="">-- Select {field.label} --</option>
                    {field.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type}
                    step={field.step}
                    required={field.required}
                    placeholder={field.placeholder}
                    value={formData[field.name] ?? ''}
                    onChange={(e) => handleInputChange(field.name, e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Section 2: Document Upload Checklist */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2 border-b pb-2">
            <Upload className="w-4 h-4 text-blue-900" />
            <span>Section 2: Document Uploads</span>
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Upload PDF or image files. The server extracts document text and shows detected fields after submission.
          </p>

          <div className="space-y-3">
            {scheme.config.required_documents?.map((doc) => {
              const selected = uploadedDocs[doc.id];
              return (
                <div
                  key={doc.id}
                  className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/70 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
                >
                  <div className="space-y-0.5">
                    <div className="text-xs font-semibold text-slate-800 flex items-center gap-2">
                      <span>{doc.name}</span>
                      {doc.required && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-medium">
                          Required
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500">{doc.description}</div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <div className="flex flex-col items-end gap-1.5 w-full sm:w-auto">
                      {selected && (
                        <div className={`flex items-center gap-2 px-2.5 py-1 rounded border text-xs font-medium ${
                          selected.uploaded && selected.ocrStatus === 'SUCCESS'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : selected.uploaded
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-slate-100 text-slate-700 border-slate-200'
                        }`}>
                          {selected.uploaded && selected.ocrStatus === 'SUCCESS' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                          <span className="truncate max-w-[180px]">{selected.file.name}</span>
                          <span>{selected.uploaded ? `OCR ${selected.ocrStatus}` : 'Ready'}</span>
                        </div>
                      )}
                      {selected?.parsedFields && Object.keys(selected.parsedFields).length > 0 && (
                        <div className="text-[10px] text-slate-600 text-right">
                          Detected: {Object.entries(selected.parsedFields).map(([key, value]) => `${key.replace(/_/g, ' ')}: ${value}`).join(' · ')}
                        </div>
                      )}
                      {selected?.failedReason && (
                        <div className="text-[10px] text-rose-700 text-right">{selected.failedReason}</div>
                      )}
                      <label className="cursor-pointer px-3 py-1.5 rounded bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-medium transition flex items-center gap-1.5">
                        <Upload className="w-3.5 h-3.5 text-slate-500" />
                        <span>{selected ? 'Replace File' : 'Choose File'}</span>
                        <input
                          type="file"
                          accept=".pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.txt"
                          className="hidden"
                          onChange={(e) => handleFileUpload(doc.id, e)}
                        />
                      </label>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {scheme.config.selection_notes?.length ? (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-950">
            <div className="font-semibold">Selection and verification notes</div>
            <ul className="list-disc pl-5 mt-2 space-y-1">
              {scheme.config.selection_notes.map((note: string) => <li key={note}>{note}</li>)}
            </ul>
            <p className="mt-2 text-[11px]">Source: {scheme.config.source_guideline}. Final eligibility and selection require authorized human verification.</p>
          </div>
        ) : null}

        {/* AI Rule Engine Sanity Check Notice */}
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-xs flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-700 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-blue-900">Automated Rule Check</div>
            <p className="text-blue-800 mt-1">
              Upon submission, configured checks flag missing information and potential eligibility mismatches for an officer. The checks do not authenticate uploaded files, determine merit ranking, or make an award decision.
            </p>
          </div>
        </div>

        {/* Submit Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onBackToSchemes}
            className="px-4 py-2.5 rounded-lg border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-100 transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-2.5 rounded-lg bg-blue-900 hover:bg-blue-800 disabled:bg-blue-400 text-white text-xs font-bold shadow transition flex items-center gap-2"
          >
            {submitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-r-transparent rounded-full animate-spin" />
                <span>Evaluating Rules & Submitting...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 text-amber-400" />
                <span>{applicationId ? 'Retry Document Uploads' : 'Submit for Rule Checks'}</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
