import React, { createContext, useCallback, useEffect, useState } from 'react';
import { apiClient, handleApiError } from '../services/api';
import { LoginRequest, User } from '../types/api';

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      await apiClient.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      // Clear local state even if API call fails
      setUser(null);
      apiClient.clearAuth();
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshAuth = useCallback(async () => {
    if (!apiClient.isAuthenticated()) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      setError(null);
      const userData = await apiClient.getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Auth refresh error:', error);
      setError(handleApiError(error));

      const status =
        (error as { status?: number })?.status ??
        (error as { response?: { status?: number } })?.response?.status ??
        (error as { cause?: { status?: number } })?.cause?.status;

      if (status === 401) {
        try {
          await apiClient.refreshToken();
          const userData = await apiClient.getCurrentUser();
          setUser(userData);
          setError(null);
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          await logout();
        }
      } else {
        console.warn('Auth refresh failed with non-auth error; retaining session.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  const login = useCallback(async (credentials: LoginRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.login(credentials);
      setUser(response.user);
    } catch (error) {
      console.error('Login error:', error);
      setError(handleApiError(error));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  // Set up automatic token refresh
  useEffect(() => {
    if (!user) return;

    const interval = setInterval(
      async () => {
        try {
          await apiClient.refreshToken();
        } catch (error) {
          console.error('Background token refresh failed:', error);
          // Don't logout automatically on background refresh failure
          // Let the user continue until they make a request that fails
        }
      },
      15 * 60 * 1000
    ); // Refresh every 15 minutes

    return () => clearInterval(interval);
  }, [user]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: Boolean(user),
    login,
    logout,
    refreshAuth,
    error,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Helper hook moved to separate file to avoid fast refresh issues

export { AuthContext };
