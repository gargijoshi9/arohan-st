export interface FormFieldConfig {
  name: string;
  label: string;
  type: 'text' | 'number' | 'email' | 'tel' | 'select';
  required: boolean;
  placeholder?: string;
  options?: string[];
  step?: string;
}

export interface RequiredDocConfig {
  id: string;
  name: string;
  required: boolean;
  description: string;
}

export interface SchemeConfig {
  code: string;
  external_code?: string;
  registry_metadata?: {
    delivery_type: string;
    scheme_type: string;
    status: string;
  };
  name: string;
  short_description: string;
  department: string;
  degree_level: string;
  tenure_years: number | null;
  stipend_amount: string;
  eligibility_rules: {
    target_category: string;
    max_annual_income: number | null;
    min_qualifying_percentage: number | null;
    max_age?: number | null;
    eligible_courses?: string[];
    eligible_degrees?: string[];
    [key: string]: any;
  };
  required_documents: RequiredDocConfig[];
  form_fields: FormFieldConfig[];
  source_guideline?: string;
  selection_notes?: string[];
}

export interface Scheme {
  id: number;
  code: string;
  name: string;
  description: string;
  degree_level: string;
  max_income: number | null;
  min_percentage: number | null;
  config: SchemeConfig;
}

export interface DocumentItem {
  id?: number;
  doc_type: string;
  file_name: string;
  file_path?: string;
  status?: string;
  extracted_text?: string | null;
  ocr_status?: 'PENDING' | 'SUCCESS' | 'PARTIAL' | 'FAILED' | string;
  ocr_confidence?: number | null;
  extraction_method?: string | null;
  parsed_fields?: Record<string, any> | null;
  failed_reason?: string | null;
  uploaded_at?: string;
}

export interface RuleMismatch {
  field: string;
  label: string;
  declared_value: any;
  expected_rule: string;
  severity: 'ERROR' | 'WARNING';
  description: string;
}

export interface RuleEvaluation {
  pass_fail: boolean;
  confidence_score: number;
  mismatches: RuleMismatch[];
  passed_checks: string[];
  summary: string;
}

export interface Application {
  id: number;
  application_no: string;
  scheme_id: number;
  scheme_code: string;
  scheme_name: string;
  applicant_id: number;
  applicant_name: string;
  applicant_email: string;
  declared_data: Record<string, any>;
  confidence_score: number;
  status: 'SUBMITTED' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'DEFICIENT' | 'SELECTED' | 'NOT_SELECTED' | string;
  ai_evaluation?: RuleEvaluation;
  admin_remarks?: string;
  created_at: string;
  updated_at: string;
  documents: DocumentItem[];
  merit_score?: number | null;
  selection_rank?: number | null;
}

export interface ApplicationSubmitPayload {
  scheme_code: string;
  full_name: string;
  email: string;
  phone?: string;
  declared_fields: Record<string, any>;
  documents: DocumentItem[];
}

export interface AdminDecisionPayload {
  decision: 'APPROVE' | 'REJECT' | 'DEFICIENT' | 'UNDER_REVIEW' | 'SELECT' | 'NOT_SELECT';
  remarks?: string;
}

export interface LoginPayload {
  role: 'applicant' | 'admin';
  email: string;
  name?: string;
  password?: string;
  otp?: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: 'applicant' | 'admin';
  email: string;
  name: string;
}

export interface NotificationItem {
  id: number;
  application_id: number;
  title: string;
  message: string;
  read_at?: string | null;
  created_at: string;
}

export interface DashboardSummary {
  total_applications: number;
  by_status: Record<string, number>;
  by_scheme: Record<string, { total: number; approved: number; deficient: number; under_review: number }>;
  active_awards: number;
  total_awards: number;
  pending_payments: number;
  generated_at: string;
}

export interface SelectionCandidate {
  application_id: number;
  application_no: string;
  applicant_name: string;
  scheme_code: string;
  status: string;
  mark_field: string | null;
  marks: number | null;
  eligible_for_ranking: boolean;
  human_decision_required: boolean;
  rank: number | null;
  within_demo_slots: boolean;
}

export interface SelectionResult {
  scheme_code: string;
  scheme_name: string;
  mark_field: string | null;
  slots: number;
  notice: string;
  candidates: SelectionCandidate[];
}

export interface AwardPaymentItem {
  id: number;
  period: string;
  amount: number;
  status: string;
  reference?: string | null;
  paid_at?: string | null;
}

export interface AwardItem {
  id: number;
  application_id: number;
  application_no: string;
  applicant_name?: string;
  applicant_email?: string;
  scheme_code: string;
  award_status: string;
  approved_amount?: number | null;
  currency: string;
  start_date?: string | null;
  end_date?: string | null;
  next_review_date?: string | null;
  officer_remarks?: string | null;
  updated_at: string;
  payments: AwardPaymentItem[];
}

export interface AwardUpdatePayload {
  award_status: string;
  approved_amount?: number;
  start_date?: string;
  end_date?: string;
  next_review_date?: string;
  officer_remarks?: string;
}

export interface PaymentCreatePayload {
  period: string;
  amount: number;
  status: string;
  reference?: string;
}
