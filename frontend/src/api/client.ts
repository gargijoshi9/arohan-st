import {
  Scheme,
  Application,
  DocumentItem,
  ApplicationSubmitPayload,
  AdminDecisionPayload,
  DocumentVerificationResult,
  LoginPayload,
  RegisterPayload,
  Session,
  Profile,
  PaginatedApplications,
  NotificationItem,
  DashboardSummary,
  SelectionResult,
  AwardItem,
  AwardUpdatePayload,
  PaymentCreatePayload
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'arohan_access_token_v1';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (!headers.has('Content-Type') && options?.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  Object.entries(authHeaders()).forEach(([name, value]) => headers.set(name, value));
  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
    try {
      const errorData = await res.json();
      if (errorData.detail) errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
    } catch {
      // Preserve the HTTP status if the response is not JSON.
    }
    throw new Error(errorMsg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  login: (payload: LoginPayload) =>
    request<Session>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),

  register: (payload: RegisterPayload) =>
    request<Session>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),

  /** The signed-in account, used to confirm a stored token is still valid. */
  getProfile: () => request<Profile>('/auth/me'),

  saveToken: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clearToken: () => localStorage.removeItem(TOKEN_KEY),
  hasToken: () => Boolean(localStorage.getItem(TOKEN_KEY)),

  uploadApplicationDocument: async (applicationId: number, docType: string, file: File) => {
    const body = new FormData();
    body.append('file', file);
    body.append('doc_type', docType);
    return request<DocumentItem>(`/applications/${applicationId}/documents`, { method: 'POST', body });
  },

  openDocument: async (filePath: string) => {
    const response = await fetch(`${API_BASE}${filePath}`, { headers: authHeaders() });
    if (!response.ok) throw new Error(`Document could not be opened (${response.status}).`);
    const objectUrl = URL.createObjectURL(await response.blob());
    window.open(objectUrl, '_blank', 'noopener,noreferrer');
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
  },

  getSchemes: () => request<Scheme[]>('/schemes'),
  getSchemeByCode: (code: string) => request<Scheme>(`/schemes/code/${code}`),
  getSchemeById: (id: number) => request<Scheme>(`/schemes/${id}`),
  submitApplication: (data: ApplicationSubmitPayload) =>
    request<Application>('/applications', { method: 'POST', body: JSON.stringify(data) }),
  getApplication: (id: number) => request<Application>(`/applications/${id}`),
  getMyApplications: () => request<Application[]>('/applications/mine'),
  getMyAwards: () => request<AwardItem[]>('/applications/awards'),
  correctApplication: (id: number, payload: { full_name: string; phone?: string; declared_fields: Record<string, unknown> }) =>
    request<Application>(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  getNotifications: () => request<NotificationItem[]>('/applications/notifications'),
  markNotificationRead: (id: number) =>
    request<{ id: number; read_at: string }>(`/applications/notifications/${id}/read`, { method: 'POST' }),
  withdrawApplication: (id: number) =>
    request<Application>(`/applications/${id}/withdraw`, { method: 'POST' }),

  getAdminQueue: (params?: {
    sort_by?: 'confidence_score' | 'created_at';
    order?: 'asc' | 'desc';
    status?: string;
    scheme_code?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    if (params?.order) query.set('order', params.order);
    if (params?.status && params.status !== 'ALL') query.set('status', params.status);
    if (params?.scheme_code && params.scheme_code !== 'ALL') query.set('scheme_code', params.scheme_code);
    if (params?.search) query.set('search', params.search);
    if (params?.page) query.set('page', String(params.page));
    if (params?.page_size) query.set('page_size', String(params.page_size));
    const qs = query.toString();
    return request<PaginatedApplications>(`/admin/queue${qs ? `?${qs}` : ''}`);
  },
  submitAdminDecision: (id: number, payload: AdminDecisionPayload) =>
    request<Application>(`/admin/applications/${id}/decision`, { method: 'POST', body: JSON.stringify(payload) }),
  verifyDocument: (documentId: number, payload: { decision: 'VERIFY' | 'DEFICIENT'; remarks: string }) =>
    request<DocumentVerificationResult>(`/admin/documents/${documentId}/verification`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  getApplicationAudit: (id: number) =>
    request<Array<{ id: number; actor_email: string; actor_role: string; action: string; from_status?: string; to_status?: string; remarks?: string; created_at: string }>>(`/admin/applications/${id}/audit`),
  getDashboard: () => request<DashboardSummary>('/admin/dashboard'),
  downloadReport: async () => {
    const response = await fetch(`${API_BASE}/admin/report.csv`, { headers: authHeaders() });
    if (!response.ok) throw new Error('The report could not be downloaded.');
    const blobUrl = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = 'arohan-application-report.csv';
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  },
  getSelection: (schemeCode: string, slots: number) =>
    request<SelectionResult>(`/admin/selection?scheme_code=${encodeURIComponent(schemeCode)}&slots=${slots}`),
  getAwards: () => request<AwardItem[]>('/admin/awards'),
  updateAward: (applicationId: number, payload: AwardUpdatePayload) =>
    request<AwardItem>(`/admin/applications/${applicationId}/award`, { method: 'PUT', body: JSON.stringify(payload) }),
  addPayment: (awardId: number, payload: PaymentCreatePayload) =>
    request<unknown>(`/admin/awards/${awardId}/payments`, { method: 'POST', body: JSON.stringify(payload) })
};
