import { EventSourcePolyfill } from 'event-source-polyfill';
import {
  ApiResponse,
  PaginatedResponse,
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  User,
  Project,
  CreateProjectRequest,
  Document,
  HealthStatus,
} from '../types/api';

const envApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const API_BASE_URL =
  typeof envApiBaseUrl === 'string' && envApiBaseUrl.trim().length > 0
    ? envApiBaseUrl
    : '/api';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiClient {
  private baseURL: string;
  private accessToken: string | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    this.loadTokenFromStorage();
  }

  private loadTokenFromStorage() {
    this.accessToken = localStorage.getItem('accessToken');
  }

  private saveTokenToStorage(token: string) {
    this.accessToken = token;
    localStorage.setItem('accessToken', token);
  }

  private removeTokenFromStorage() {
    this.accessToken = null;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
        ...(this.accessToken && {
          Authorization: `Bearer ${this.accessToken}`,
        }),
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        let errorData: Record<string, unknown> = {};
        try {
          errorData = await response.json();
        } catch {
          // If parsing fails, use status text
          errorData = { message: response.statusText };
        }

        const message =
          typeof errorData.message === 'string' ? errorData.message : 'Request failed';
        const code = typeof errorData.code === 'string' ? errorData.code : undefined;
        const details =
          errorData.details && typeof errorData.details === 'object'
            ? (errorData.details as Record<string, unknown>)
            : undefined;

        throw new ApiError(message, response.status, code, details);
      }

      // Handle empty responses (e.g., 204 No Content)
      if (response.status === 204) {
        return {} as T;
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Network error', 0, 'NETWORK_ERROR');
    }
  }

  // Authentication Methods
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<ApiResponse<LoginResponse>>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    this.saveTokenToStorage(response.data.accessToken);
    localStorage.setItem('refreshToken', response.data.refreshToken);

    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch (error) {
      // Continue with logout even if API call fails
      console.warn('Logout API call failed:', error);
    } finally {
      this.removeTokenFromStorage();
    }
  }

  async refreshToken(): Promise<string> {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      throw new ApiError('No refresh token available', 401);
    }

    const response = await this.request<ApiResponse<{ accessToken: string }>>(
      '/auth/refresh',
      {
        method: 'POST',
        body: JSON.stringify({ refreshToken } as RefreshTokenRequest),
      }
    );

    this.saveTokenToStorage(response.data.accessToken);
    return response.data.accessToken;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.request<ApiResponse<User>>('/auth/me');
    return response.data;
  }

  // Project Methods
  async getProjects(
    page = 1,
    pageSize = 20,
    search?: string
  ): Promise<PaginatedResponse<Project>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      ...(search && { search }),
    });

    const response = await this.request<PaginatedResponse<Project>>(
      `/projects?${params}`
    );
    return response;
  }

  async getProject(id: string): Promise<Project> {
    const response = await this.request<ApiResponse<Project>>(`/projects/${id}`);
    return response.data;
  }

  async createProject(data: CreateProjectRequest): Promise<Project> {
    const response = await this.request<ApiResponse<Project>>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.data;
  }

  async updateProject(
    id: string,
    data: Partial<CreateProjectRequest>
  ): Promise<Project> {
    const response = await this.request<ApiResponse<Project>>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return response.data;
  }

  async deleteProject(id: string): Promise<void> {
    await this.request(`/projects/${id}`, { method: 'DELETE' });
  }

  async startProjectProcessing(id: string): Promise<void> {
    await this.request(`/projects/${id}/process`, { method: 'POST' });
  }

  // Document Methods
  async getProjectDocuments(projectId: string): Promise<Document[]> {
    const response = await this.request<ApiResponse<Document[]>>(
      `/projects/${projectId}/documents`
    );
    return response.data;
  }

  async getDocument(projectId: string, documentId: string): Promise<Document> {
    const response = await this.request<ApiResponse<Document>>(
      `/projects/${projectId}/documents/${documentId}`
    );
    return response.data;
  }

  async updateDocument(
    projectId: string,
    documentId: string,
    content: string
  ): Promise<Document> {
    const response = await this.request<ApiResponse<Document>>(
      `/projects/${projectId}/documents/${documentId}`,
      {
        method: 'PUT',
        body: JSON.stringify({ content }),
      }
    );
    return response.data;
  }

  async regenerateDocument(projectId: string, documentId: string): Promise<void> {
    await this.request(`/projects/${projectId}/documents/${documentId}/regenerate`, {
      method: 'POST',
    });
  }

  // Health Check
  async getHealthStatus(): Promise<HealthStatus> {
    const response = await this.request<HealthStatus>('/health');
    return response;
  }

  // Server-Sent Events for Progress Updates
  createProgressEventSource(projectId: string): EventSource {
    const token = this.getAccessToken();
    const base = this.baseURL.replace(/\/$/, '');
    const url = `${base}/projects/${projectId}/progress`;

    const headers: Record<string, string> = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    return new EventSourcePolyfill(url, { headers }) as EventSource;
  }

  // Token management
  setAccessToken(token: string) {
    this.saveTokenToStorage(token);
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  isAuthenticated(): boolean {
    return Boolean(this.accessToken);
  }

  clearAuth() {
    this.removeTokenFromStorage();
  }
}

// Create singleton instance
export const apiClient = new ApiClient(API_BASE_URL);

// Export types for use in components
export { ApiError };

// Helper function for handling API errors
export const handleApiError = (error: unknown): string => {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
};
