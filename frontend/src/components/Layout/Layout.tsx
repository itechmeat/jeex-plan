import React, { useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';
import { appConfig } from '../../config/appConfig';
import { ROUTES } from '../../config/routes';
import { Button } from '../ui/Button/Button';
import classNames from 'classnames';
import buttonStyles from '../ui/Button/Button.module.scss';
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
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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
    setIsLoggingOut(true);
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      // Always redirect to login, even if logout API fails
      // Use replace: true to prevent back-navigation to protected pages
      navigate(ROUTES.LOGIN, { replace: true });
      setIsLoggingOut(false);
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
            <h1 className={styles.brandTitle}>
              <Link
                to={ROUTES.DASHBOARD}
                className={styles.brandLink}
                aria-label={`Navigate to ${resolvedBrandTitle} dashboard`}
              >
                {resolvedBrandTitle}
              </Link>
            </h1>
            <span className={styles.brandSubtitle}>{resolvedBrandSubtitle}</span>
          </div>

          <nav className={styles.nav}>
            <Link
              to={ROUTES.DASHBOARD}
              className={classNames(
                buttonStyles.button,
                buttonStyles.ghost,
                buttonStyles.md
              )}
            >
              Dashboard
            </Link>
            <Link
              to={ROUTES.PROJECTS}
              className={classNames(
                buttonStyles.button,
                buttonStyles.ghost,
                buttonStyles.md
              )}
            >
              Projects
            </Link>
            <Link
              to={ROUTES.HEALTH}
              className={classNames(
                buttonStyles.button,
                buttonStyles.ghost,
                buttonStyles.md
              )}
            >
              System Health
            </Link>
            <Link
              to={ROUTES.PROJECTS_NEW}
              className={classNames(
                buttonStyles.button,
                buttonStyles.primary,
                buttonStyles.md
              )}
            >
              New Project
            </Link>
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
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleLogout}
                  isLoading={isLoggingOut}
                  disabled={isLoggingOut}
                >
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
            <Link to={ROUTES.HEALTH} className={styles.footerLink}>
              System Status
            </Link>
            <Link to={ROUTES.TERMS}>Terms</Link>
            <Link to={ROUTES.PRIVACY}>Privacy</Link>
            <Link to={ROUTES.SUPPORT}>Support</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};
