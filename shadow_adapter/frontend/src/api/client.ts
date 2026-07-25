import {
  ContractorPublic,
  HealthResponse,
  LoginResponse,
  ShadowAuditEntry,
  ShadowTask,
  TaskSubmitResponse,
} from '../types';

const API_BASE = '/api/v1';

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

export class APIClient {
  private getToken(): string | null {
    return localStorage.getItem('shadow_token');
  }

  public setToken(token: string): void {
    localStorage.setItem('shadow_token', token);
  }

  public clearToken(): void {
    localStorage.removeItem('shadow_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Do not override Content-Type for FormData uploads
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      throw new APIError(401, 'Unauthorized — Session expired');
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = data.detail || response.statusText || 'API request failed';
      throw new APIError(response.status, errorMsg);
    }

    return data as T;
  }

  // Auth endpoints
  async login(username: string, password: string): Promise<LoginResponse> {
    const data = await this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async register(username: string, password: string, email?: string): Promise<ContractorPublic> {
    return this.request<ContractorPublic>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, email }),
    });
  }

  async getMe(): Promise<ContractorPublic> {
    return this.request<ContractorPublic>('/auth/me');
  }

  // Task endpoints
  async getTasks(params: { status?: string; assigned_to_me?: boolean; limit?: number } = {}): Promise<ShadowTask[]> {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.assigned_to_me) query.append('assigned_to_me', 'true');
    if (params.limit) query.append('limit', params.limit.toString());
    const queryStr = query.toString() ? `?${query.toString()}` : '';
    return this.request<ShadowTask[]>(`/tasks${queryStr}`);
  }

  async getTask(id: string): Promise<ShadowTask> {
    return this.request<ShadowTask>(`/tasks/${id}`);
  }

  async claimTask(id: string): Promise<ShadowTask> {
    return this.request<ShadowTask>(`/tasks/${id}/claim`, { method: 'POST' });
  }

  async unclaimTask(id: string): Promise<ShadowTask> {
    return this.request<ShadowTask>(`/tasks/${id}/unclaim`, { method: 'POST' });
  }

  async submitTask(
    id: string,
    deliverableText: string,
    files: File[]
  ): Promise<TaskSubmitResponse> {
    const formData = new FormData();
    formData.append('deliverable_text', deliverableText);
    files.forEach((file) => formData.append('files', file));

    return this.request<TaskSubmitResponse>(`/tasks/${id}/submit`, {
      method: 'POST',
      body: formData,
    });
  }

  async getAuditLog(id: string): Promise<ShadowAuditEntry[]> {
    return this.request<ShadowAuditEntry[]>(`/tasks/${id}/audit`);
  }

  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }
}

export const api = new APIClient();
export const apiClient = api;
