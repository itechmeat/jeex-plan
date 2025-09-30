import React, { createContext, useCallback, useEffect, useState } from 'react';
import { apiClient, handleApiError } from '../services/api';
import { LoginRequest, RegisterRequest, User } from '../types/api';

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
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
      // Production-safe error logging
      if (import.meta.env.DEV) {
        console.error('Logout error:', error);
      }

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
      setError(null);
      return;
    }

    try {
      setError(null);
      const userData = await apiClient.getCurrentUser();
      setUser(userData);
    } catch (error) {
      // Production-safe error logging
      if (import.meta.env.DEV) {
        console.error('Auth refresh error:', error);
      }
      setError(handleApiError(error));

      // Robust status code extraction from various error types
      const extractStatus = (error: unknown): number | null => {
        if (error && typeof error === 'object') {
          const errorObj = error as Record<string, unknown>;

          // Direct status property
          if (typeof errorObj.status === 'number') {
            return errorObj.status;
          }

          // Response status property
          if (errorObj.response && typeof errorObj.response === 'object') {
            const response = errorObj.response as Record<string, unknown>;
            if (typeof response.status === 'number') {
              return response.status;
            }
          }

          // Cause status property
          if (errorObj.cause && typeof errorObj.cause === 'object') {
            const cause = errorObj.cause as Record<string, unknown>;
            if (typeof cause.status === 'number') {
              return cause.status;
            }
          }
        }

        return null;
      };

      const status = extractStatus(error);

      if (status === 401) {
        try {
          await apiClient.refreshToken();
          const userData = await apiClient.getCurrentUser();
          setUser(userData);
          setError(null);
        } catch (refreshError) {
          // Production-safe error logging
          if (import.meta.env.DEV) {
            console.error('Token refresh failed:', refreshError);
          }
          await logout();
        }
      } else {
        // Production-safe logging for non-auth errors
        if (import.meta.env.DEV) {
          console.warn('Auth refresh failed with non-auth error; retaining session.');
        }
        // For non-auth errors (network timeouts, 5xx, etc.), do not clear the session
        // This prevents accidental logouts due to temporary network issues
      }
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  const login = useCallback(async (credentials: LoginRequest) => {
    // Production-safe logging
    if (import.meta.env.DEV) {
      console.log('AuthContext: Starting login');
    }
    setError(null);

    try {
      const response = await apiClient.login(credentials);
      if (import.meta.env.DEV) {
        console.log('AuthContext: Login successful');
      }
      setUser(response.user);
    } catch (error) {
      // Production-safe error logging
      if (import.meta.env.DEV) {
        console.error('AuthContext: Login error:', error);
        const errorMessage = handleApiError(error);
        console.log('AuthContext: Setting error message:', errorMessage);
      }
      setError(handleApiError(error));
      throw error;
    }
  }, []);

  const register = useCallback(async (userData: RegisterRequest) => {
    setError(null);

    try {
      const response = await apiClient.register(userData);
      setUser(response.user);
    } catch (error) {
      // Production-safe error logging
      if (import.meta.env.DEV) {
        console.error('Registration error:', error);
      }
      setError(handleApiError(error));
      throw error;
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  // Set up automatic token refresh with improved security
  useEffect(() => {
    if (!user) return;

    // Read refresh interval from environment variable with validation
    const envInterval = import.meta.env.VITE_TOKEN_REFRESH_INTERVAL;
    const parsedInterval = parseInt(envInterval, 10);
    const refreshInterval =
      !isNaN(parsedInterval) && parsedInterval > 0 ? parsedInterval : 30 * 60 * 1000; // Default to 30 minutes

    const interval = setInterval(async () => {
      try {
        await apiClient.refreshToken();
        if (import.meta.env.DEV) {
          console.log('Background token refresh successful');
        }
      } catch (error) {
        // Production-safe error logging
        if (import.meta.env.DEV) {
          console.error('Background token refresh failed:', error);
        }
        // Robust status code extraction for security
        const extractStatus = (error: unknown): number | null => {
          if (error && typeof error === 'object') {
            const errorObj = error as Record<string, unknown>;

            // Direct status property
            if (typeof errorObj.status === 'number') {
              return errorObj.status;
            }

            // Response status property
            if (errorObj.response && typeof errorObj.response === 'object') {
              const response = errorObj.response as Record<string, unknown>;
              if (typeof response.status === 'number') {
                return response.status;
              }
            }
          }

          return null;
        };

        const status = extractStatus(error);

        if (status === 401) {
          if (import.meta.env.DEV) {
            console.warn('Token refresh failed with 401, logging out user');
          }
          logout();
        }
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [user, logout]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: Boolean(user),
    login,
    register,
    logout,
    refreshAuth,
    error,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Helper hook moved to separate file to avoid fast refresh issues

export { AuthContext };
