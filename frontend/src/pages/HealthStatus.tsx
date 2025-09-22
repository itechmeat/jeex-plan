import React, { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Server, Database, Activity, AlertCircle } from 'lucide-react'
import styles from './HealthStatus.module.scss'

interface HealthCheck {
  service: string
  endpoint: string
  status: 'pass' | 'fail' | 'warn'
  responseTime: number
  details: string
  timestamp: string
}

const HealthStatus: React.FC = () => {
  const [healthChecks, setHealthChecks] = useState<HealthCheck[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHealthStatus()
    const interval = setInterval(fetchHealthStatus, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchHealthStatus = async () => {
    try {
      const response = await fetch('/api/system/status')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      // Transform data to required format
      const healthChecks: HealthCheck[] = data.services.map((service: any) => ({
        service: service.service,
        endpoint: service.endpoint,
        status: service.status,
        responseTime: service.responseTime,
        details: service.details,
        timestamp: new Date(service.timestamp * 1000).toISOString()
      }))

      setHealthChecks(healthChecks)
    } catch (error) {
      console.error('Failed to fetch health status:', error)
      // Show error to user
      setHealthChecks([{
        service: 'System Status',
        endpoint: '/api/system/status',
        status: 'fail',
        responseTime: 0,
        details: `Failed to load status: ${error}`,
        timestamp: new Date().toISOString()
      }])
    } finally {
      setLoading(false)
    }
  }

  const getServiceIcon = (serviceName: string) => {
    if (serviceName.includes('Frontend')) return <Server className={styles.serviceIcon} />
    if (serviceName.includes('API') || serviceName.includes('Backend')) return <Activity className={styles.serviceIcon} />
    if (serviceName.includes('PostgreSQL') || serviceName.includes('Qdrant') || serviceName.includes('Redis')) return <Database className={styles.serviceIcon} />
    return <AlertCircle className={styles.serviceIcon} />
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
        return <CheckCircle className={`${styles.alertIcon} ${styles.success}`} />
      case 'warn':
        return <AlertTriangle className={`${styles.alertIcon} ${styles.warning}`} />
      case 'fail':
        return <XCircle className={`${styles.alertIcon} ${styles.error}`} />
      default:
        return <AlertCircle className={`${styles.alertIcon} ${styles.error}`} />
    }
  }

  const getOverallStatus = () => {
    if (healthChecks.length === 0) return 'unknown'

    const hasFailures = healthChecks.some(check => check.status === 'fail')
    const hasWarnings = healthChecks.some(check => check.status === 'warn')

    if (hasFailures) return 'error'
    if (hasWarnings) return 'warning'
    return 'success'
  }

  const getOverallMessage = () => {
    const overallStatus = getOverallStatus()
    const totalServices = healthChecks.length
    const healthyServices = healthChecks.filter(check => check.status === 'pass').length

    switch (overallStatus) {
      case 'success':
        return `All systems operational (${totalServices}/${totalServices} services healthy)`
      case 'warning':
        return `Some services have issues (${healthyServices}/${totalServices} services healthy)`
      case 'error':
        return `Critical issues detected (${healthyServices}/${totalServices} services healthy)`
      default:
        return 'Status unknown'
    }
  }

  if (loading) {
    return (
      <div className={styles.healthStatus}>
        <div className={styles.container}>
          <div className={styles.loading}>
            <RefreshCw className={styles.loadingIcon} />
            <span>Loading health status...</span>
          </div>
        </div>
      </div>
    )
  }

  const overallStatus = getOverallStatus()

  return (
    <div className={styles.healthStatus}>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>System Health Status</h1>
          <p>Real-time monitoring of JEEX Plan infrastructure components</p>
        </div>

        {/* Overall Status Alert */}
        <div className={`${styles.alertBanner} ${styles[overallStatus]}`}>
          <div className={styles.alertContent}>
            {getStatusIcon(overallStatus === 'success' ? 'pass' : overallStatus === 'warning' ? 'warn' : 'fail')}
            <span className={`${styles.alertText} ${styles[overallStatus]}`}>
              {getOverallMessage()}
            </span>
          </div>
        </div>

        {/* Health Checks Grid */}
        <div className={styles.healthGrid}>
          {healthChecks.map((check) => (
            <div key={check.service} className={styles.healthCard}>
              <div className={styles.healthCardHeader}>
                <div className={styles.serviceInfo}>
                  {getServiceIcon(check.service)}
                  <h3>{check.service}</h3>
                </div>
                <div className={styles.responseTime}>
                  {check.responseTime}ms
                </div>
              </div>

              <div className={styles.healthCardBody}>
                <div className={styles.endpoint}>
                  {check.endpoint}
                </div>

                <div className={`${styles.status} ${styles[check.status]}`}>
                  {check.status === 'pass' ? 'Service operational' :
                   check.status === 'warn' ? 'Performance issues' :
                   'Server disconnected'}
                </div>

                <div className={`${styles.details} ${styles[check.status]}`}>
                  {check.details}
                </div>

                <p className={styles.timestamp}>
                  Last checked: {new Date(check.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default HealthStatus