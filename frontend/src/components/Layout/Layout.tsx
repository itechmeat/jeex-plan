import React from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';
import { appConfig } from '../../config/appConfig';
import { Button } from '../ui/Button/Button';
import styles from './Layout.module.scss';

type LayoutProps = {
  appName?: string;
  brandTitle?: string;
  brandSubtitle?: string;
  copyrightYear?: number;
};

export const Layout: React.FC<LayoutProps> = ({
  appName,
  brandTitle,
  brandSubtitle,
  copyrightYear,
}) => {
  const navigate = useNavigate();
  const { user, logout, isLoading } = useAuth();

  const currentYear = new Date().getFullYear();
  const envYearValue = import.meta.env.VITE_APP_COPYRIGHT_YEAR;
  const parsedEnvYear = envYearValue ? Number.parseInt(envYearValue, 10) : NaN;
  const resolvedAppName = appName?.trim() || appConfig.appTitle;
  const resolvedBrandTitle = brandTitle?.trim() || appConfig.brandTitle;
  const resolvedBrandSubtitle = brandSubtitle?.trim() || appConfig.brandSubtitle;
  const resolvedYear =
    copyrightYear ??
    (Number.isFinite(parsedEnvYear) ? parsedEnvYear : undefined) ??
    currentYear;

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinner} />
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.brand}>
            <h1
              className={styles.brandTitle}
              tabIndex={0}
              role="button"
              aria-label={`Navigate to ${resolvedBrandTitle} dashboard`}
              onClick={() => navigate('/dashboard')}
              onKeyDown={event => {
                if (event.key === 'Enter') {
                  navigate('/dashboard');
                }
                if (event.key === ' ' || event.key === 'Spacebar') {
                  event.preventDefault();
                  navigate('/dashboard');
                }
              }}
            >
              {resolvedBrandTitle}
            </h1>
            <span className={styles.brandSubtitle}>{resolvedBrandSubtitle}</span>
          </div>

          <nav className={styles.nav}>
            <Button variant="ghost" onClick={() => navigate('/dashboard')}>
              Dashboard
            </Button>
            <Button variant="ghost" onClick={() => navigate('/projects')}>
              Projects
            </Button>
            <Button variant="ghost" onClick={() => navigate('/health')}>
              System Health
            </Button>
            <Button variant="primary" onClick={() => navigate('/projects/new')}>
              New Project
            </Button>
          </nav>

          <div className={styles.userSection}>
            {user && (
              <>
                <div className={styles.userInfo}>
                  <span className={styles.userName}>
                    {user.firstName} {user.lastName}
                  </span>
                  <span className={styles.userEmail}>{user.email}</span>
                </div>
                <Button variant="outline" size="sm" onClick={handleLogout}>
                  Logout
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className={styles.main}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerContent}>
          <p>
            &copy; {resolvedYear} {resolvedAppName}. All rights reserved.
          </p>
          <div className={styles.footerLinks}>
            <button className={styles.footerLink} onClick={() => navigate('/health')}>
              System Status
            </button>
            <Link to="/terms">Terms</Link>
            <Link to="/privacy">Privacy</Link>
            <Link to="/support">Support</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};
