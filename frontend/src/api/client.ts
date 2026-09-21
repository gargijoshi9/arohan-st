import {
  Scheme,
  Application,
  ApplicationSubmitPayload,
  AdminDecisionPayload
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {})
      }
    });

    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData.detail) {
          errorMsg = typeof errorData.detail === 'string' 
            ? errorData.detail 
            : JSON.stringify(errorData.detail);
        }
      } catch {
        // ignore fallback
      }
      throw new Error(errorMsg);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  getSchemes: () => request<Scheme[]>('/schemes'),
  
  getSchemeByCode: (code: string) => request<Scheme>(`/schemes/code/${code}`),
  
  getSchemeById: (id: number) => request<Scheme>(`/schemes/${id}`),
  
  submitApplication: (data: ApplicationSubmitPayload) =>
    request<Application>('/applications', {
      method: 'POST',
      body: JSON.stringify(data)
    }),

  getApplication: (id: number) => request<Application>(`/applications/${id}`),

  getApplicationsByEmail: (email: string) =>
    request<Application[]>(`/applications/by-email/${encodeURIComponent(email)}`),

  getAdminQueue: (params?: {
    sort_by?: 'confidence_score' | 'created_at';
    order?: 'asc' | 'desc';
    status?: string;
    scheme_code?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    if (params?.order) query.set('order', params.order);
    if (params?.status && params.status !== 'ALL') query.set('status', params.status);
    if (params?.scheme_code && params.scheme_code !== 'ALL') query.set('scheme_code', params.scheme_code);
    
    const qs = query.toString();
    return request<Application[]>(`/admin/queue${qs ? `?${qs}` : ''}`);
  },

  submitAdminDecision: (id: number, payload: AdminDecisionPayload) =>
    request<Application>(`/admin/applications/${id}/decision`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
};
