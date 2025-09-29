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
      setError(null);
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
        // For non-auth errors during refresh, clear user to avoid stuck loading state
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  const login = useCallback(async (credentials: LoginRequest) => {
    console.log('AuthContext: Starting login');
    setError(null);

    try {
      const response = await apiClient.login(credentials);
      console.log('AuthContext: Login successful');
      setUser(response.user);
    } catch (error) {
      console.error('AuthContext: Login error:', error);
      const errorMessage = handleApiError(error);
      console.log('AuthContext: Setting error message:', errorMessage);
      setError(errorMessage);
      throw error;
    }
  }, []);

  const register = useCallback(async (userData: RegisterRequest) => {
    setError(null);

    try {
      const response = await apiClient.register(userData);
      setUser(response.user);
    } catch (error) {
      console.error('Registration error:', error);
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

    // SECURITY: Reduced refresh interval to 30 minutes for better rotation
    // TODO: Implement proactive refresh when token is close to expiry
    const interval = setInterval(
      async () => {
        try {
          await apiClient.refreshToken();
          console.log('Background token refresh successful');
        } catch (error) {
          console.error('Background token refresh failed:', error);
          // SECURITY: On repeated failures, logout user to prevent stale session
          // This prevents attackers from maintaining access with compromised tokens
          if (error instanceof Error && error.message.includes('401')) {
            console.warn('Token refresh failed with 401, logging out user');
            logout();
          }
        }
      },
      30 * 60 * 1000
    );

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
