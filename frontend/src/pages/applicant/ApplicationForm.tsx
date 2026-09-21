import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Scheme, DocumentItem } from '../../api/types';
import { useAuth } from '../../hooks/useAuth';
import { 
  FileText, 
  Upload, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  Sparkles, 
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
  const [selectedSchemeCode, setSelectedSchemeCode] = useState<string>(initialSchemeCode);
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [uploadedDocs, setUploadedDocs] = useState<Record<string, { fileName: string; filePath: string }>>({});

  useEffect(() => {
    loadScheme(selectedSchemeCode);
  }, [selectedSchemeCode]);

  const loadScheme = async (code: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSchemeByCode(code);
      setScheme(data);
      
      // Initialize default values
      const initial: Record<string, any> = {
        full_name: user?.name || '',
        email: user?.email || '',
        category: user?.category || 'ST',
        caste_certificate_no: 'ST/JH/2023/88921',
        annual_family_income: 280000,
      };

      if (code === 'NFST') {
        initial.course_enrolled = 'Ph.D';
        initial.university_name = 'Jawaharlal Nehru University, New Delhi';
        initial.research_topic = 'Tribal Ethnobotany & Traditional Ecological Knowledge';
        initial.admission_year = 2024;
        initial.pg_percentage = 66.5;
      } else if (code === 'NOS') {
        initial.applicant_age = 28;
        initial.destination_country = 'United Kingdom';
        initial.foreign_university = 'University of Edinburgh';
        initial.foreign_course = 'MSc in Ecological Economics';
        initial.has_unconditional_offer = 'Yes';
        initial.qualifying_percentage = 68.0;
        initial.passport_number = 'Z8877665';
      }

      setFormData(initial);

      // Pre-attach default sample document references
      const sampleDocs: Record<string, { fileName: string; filePath: string }> = {};
      data.config.required_documents.forEach((d) => {
        sampleDocs[d.id] = {
          fileName: `${d.id}_verified_sample.pdf`,
          filePath: `/sample-documents/${d.id}_sample.txt`
        };
      });
      setUploadedDocs(sampleDocs);
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
    if (file) {
      setUploadedDocs((prev) => ({
        ...prev,
        [docId]: {
          fileName: file.name,
          filePath: `/uploads/${file.name}`
        }
      }));
    }
  };

  // Demo auto-fill helpers
  const handleAutoFillCompliant = () => {
    if (selectedSchemeCode === 'NFST') {
      setFormData({
        full_name: 'Ramesh Chandra Munda',
        email: 'ramesh.munda@example.edu',
        phone: '9876543210',
        category: 'ST',
        caste_certificate_no: 'ST/JH/2023/88921',
        annual_family_income: 280000,
        course_enrolled: 'Ph.D',
        university_name: 'Jawaharlal Nehru University, New Delhi',
        research_topic: 'Tribal Ethnobotany of Chota Nagpur Plateau',
        admission_year: 2024,
        pg_percentage: 67.5
      });
    } else {
      setFormData({
        full_name: 'Sunita Devi Soren',
        email: 'sunita.soren@example.com',
        phone: '9811223344',
        category: 'ST',
        caste_certificate_no: 'ST/OD/2022/45109',
        applicant_age: 27,
        annual_family_income: 340000,
        destination_country: 'United Kingdom',
        foreign_university: 'University of Edinburgh',
        foreign_course: 'MSc in Ecological Economics',
        has_unconditional_offer: 'Yes',
        qualifying_percentage: 71.2,
        passport_number: 'Z6543219'
      });
    }
  };

  const handleAutoFillDiscrepancy = () => {
    // Deliberately triggers AI rule engine mismatches:
    // Income > 6L, qualifying percentage < threshold
    if (selectedSchemeCode === 'NFST') {
      setFormData({
        full_name: 'Test Discrepancy Applicant',
        email: 'test.flagged@example.com',
        phone: '9988776655',
        category: 'General', // Ineligible category!
        caste_certificate_no: '', // Missing caste cert!
        annual_family_income: 850000, // Exceeds 6L cap!
        course_enrolled: 'Ph.D',
        university_name: 'State University',
        research_topic: 'Solar Materials',
        admission_year: 2024,
        pg_percentage: 49.0 // Below 55% min!
      });
    } else {
      setFormData({
        full_name: 'Amit Tirkey (Flagged Test)',
        email: 'amit.tirkey@example.com',
        phone: '9933445566',
        category: 'ST',
        caste_certificate_no: 'ST/CG/2021/11029',
        applicant_age: 38, // Exceeds 35 age limit!
        annual_family_income: 820000, // Exceeds 6L cap!
        destination_country: 'Australia',
        foreign_university: 'University of Melbourne',
        foreign_course: 'Master of Environmental Science',
        has_unconditional_offer: 'No', // Missing unconditional offer!
        qualifying_percentage: 52.5, // Below 60% min!
        passport_number: 'T9988771'
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheme) return;

    setSubmitting(true);
    setError(null);

    try {
      // Build document array
      const docPayload: DocumentItem[] = Object.entries(uploadedDocs).map(([docType, fileInfo]) => ({
        doc_type: docType,
        file_name: fileInfo.fileName,
        file_path: fileInfo.filePath,
        status: 'UPLOADED'
      }));

      const payload = {
        scheme_code: scheme.code,
        full_name: formData.full_name || user?.name || 'Applicant',
        email: formData.email || user?.email || 'applicant@example.com',
        phone: formData.phone || '',
        declared_fields: formData,
        documents: docPayload
      };

      const result = await api.submitApplication(payload);
      onSubmitSuccess(result.id);
    } catch (err: any) {
      setError(err.message || 'Failed to submit application');
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

        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500 font-medium">Scheme:</label>
          <select
            value={selectedSchemeCode}
            onChange={(e) => setSelectedSchemeCode(e.target.value)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="NFST">NFST (National Fellowship for ST Students)</option>
            <option value="NOS">NOS (National Overseas Scholarship for ST)</option>
          </select>
        </div>
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

        {/* Quick Demo Pre-fills */}
        <div className="mt-4 pt-3 border-t border-blue-800 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-blue-300 font-medium flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            Demo Test Controls:
          </span>
          <button
            type="button"
            onClick={handleAutoFillCompliant}
            className="px-2.5 py-1 rounded bg-emerald-700/80 hover:bg-emerald-600 text-white font-medium text-[11px] transition"
          >
            Fill 100% Compliant Data
          </button>
          <button
            type="button"
            onClick={handleAutoFillDiscrepancy}
            className="px-2.5 py-1 rounded bg-rose-700/80 hover:bg-rose-600 text-white font-medium text-[11px] transition"
          >
            Fill Discrepant Data (Income/Category Flags)
          </button>
        </div>
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
            These values are evaluated in real time by the AROHAN-ST AI Rule Engine against statutory scheme caps.
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
            <span>Section 2: Verifiable Document Proofs (Mock Upload)</span>
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            In this prototype, uploaded document names and metadata are tracked and verified against statutory rules.
          </p>

          <div className="space-y-3">
            {scheme.config.required_documents?.map((doc) => {
              const uploaded = uploadedDocs[doc.id];
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
                    {uploaded ? (
                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="truncate max-w-[150px]">{uploaded.fileName}</span>
                      </div>
                    ) : (
                      <label className="cursor-pointer px-3 py-1.5 rounded bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-medium transition flex items-center gap-1.5">
                        <Upload className="w-3.5 h-3.5 text-slate-500" />
                        <span>Choose File</span>
                        <input
                          type="file"
                          className="hidden"
                          onChange={(e) => handleFileUpload(doc.id, e)}
                        />
                      </label>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Rule Engine Sanity Check Notice */}
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-xs flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-700 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-blue-900">Automated AI Eligibility Evaluation Note</div>
            <p className="text-blue-800 mt-1">
              Upon clicking "Submit Application", the AROHAN-ST rule engine will automatically evaluate your declared income,
              qualifying marks, ST certificate, and age against MoTA scheme criteria to generate a verification confidence score
              for the officer review queue.
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
                <span>Submit & Run AI Verification</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
