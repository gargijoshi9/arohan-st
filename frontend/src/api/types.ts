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
  status: 'SUBMITTED' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'DEFICIENT';
  ai_evaluation?: RuleEvaluation;
  admin_remarks?: string;
  created_at: string;
  updated_at: string;
  documents: DocumentItem[];
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
  decision: 'APPROVE' | 'REJECT' | 'DEFICIENT' | 'UNDER_REVIEW';
  remarks?: string;
}
