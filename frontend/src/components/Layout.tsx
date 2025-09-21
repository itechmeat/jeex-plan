import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import styles from './Layout.module.scss'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation()

  return (
    <div className={styles.layout}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContainer}>
          <div className={styles.headerContent}>
            <div className={styles.brand}>
              <h1>JEEX Plan</h1>
            </div>
            <nav className={styles.nav}>
              <Link
                to="/"
                className={`${styles.navLink} ${
                  location.pathname === '/' ? styles.active : styles.inactive
                }`}
              >
                Dashboard
              </Link>
              <Link
                to="/health"
                className={`${styles.navLink} ${
                  location.pathname === '/health' ? styles.active : styles.inactive
                }`}
              >
                Health Status
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className={styles.main}>
        {children}
      </main>
    </div>
  )
}

export default Layout