import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { AUTH_MESSAGES } from '../config/constants';
import { ROUTES } from '../config/routes';
import { useAuth } from '../contexts/useAuth';
import styles from './AuthLoader.module.css';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className={styles.loaderContainer}>
        <div className={styles.spinner} />
        <p className={styles.message} role='status' aria-live='polite'>
          {AUTH_MESSAGES.CHECKING_AUTHENTICATION}
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect them to the login page, but save the attempted location
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
