import React, { useState, useEffect } from 'react'
import { Server, Database, Activity, AlertCircle, RefreshCw } from 'lucide-react'
import styles from './Dashboard.module.scss'

interface ServiceStatus {
  name: string
  status: 'healthy' | 'unhealthy' | 'degraded'
  responseTime: number
  lastCheck: string
  icon: React.ReactNode
}

const Dashboard: React.FC = () => {
  const [services, setServices] = useState<ServiceStatus[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchServicesStatus()
    const interval = setInterval(fetchServicesStatus, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchServicesStatus = async () => {
    try {
      const response = await fetch('/api/system/status')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      const servicesData: ServiceStatus[] = data.services.map((service: any) => ({
        name: service.service,
        status: service.status === 'pass' ? 'healthy' : service.status === 'warn' ? 'degraded' : 'unhealthy',
        responseTime: service.responseTime,
        lastCheck: new Date(service.timestamp * 1000).toISOString(),
        icon: getServiceIcon(service.service)
      }))

      setServices(servicesData)
    } catch (error) {
      console.error('Failed to fetch services status:', error)
      // Show error to user
      setServices([{
        name: 'System Status',
        status: 'unhealthy',
        responseTime: 0,
        lastCheck: new Date().toISOString(),
        icon: <AlertCircle className="w-5 h-5" />
      }])
    } finally {
      setLoading(false)
    }
  }

  const getServiceIcon = (serviceName: string) => {
    if (serviceName.includes('Frontend')) return <Server className="w-5 h-5" />
    if (serviceName.includes('API') || serviceName.includes('Backend')) return <Activity className="w-5 h-5" />
    if (serviceName.includes('PostgreSQL') || serviceName.includes('Qdrant') || serviceName.includes('Redis')) return <Database className="w-5 h-5" />
    return <AlertCircle className="w-5 h-5" />
  }

  const getEndpointFromService = (serviceName: string) => {
    const endpoints: Record<string, string> = {
      'API Backend': 'http://localhost:8000/health',
      'PostgreSQL': 'localhost:5432',
      'Qdrant': 'http://localhost:6333/',
      'Redis': 'localhost:6379',
      'Vault': 'http://localhost:8200/v1/sys/health',
      'Frontend': 'http://localhost:5200'
    }
    return endpoints[serviceName] || 'Unknown'
  }

  // Calculate statistics based on real data
  const totalServices = services.length
  const healthyServices = services.filter(s => s.status === 'healthy').length
  const degradedServices = services.filter(s => s.status === 'degraded').length
  const unhealthyServices = services.filter(s => s.status === 'unhealthy').length
  const avgResponseTime = services.length > 0
    ? Math.round(services.reduce((sum, s) => sum + s.responseTime, 0) / services.length)
    : 0

  if (loading) {
    return (
      <div className={styles.loading}>
        <RefreshCw className={styles.loadingIcon} />
        <span>Loading dashboard...</span>
      </div>
    )
  }

  return (
    <div className={styles.dashboard}>
      <div className={styles.container}>
        <div className={styles.header}>
          <div className={styles.headerContent}>
            <h1>JEEX Plan Dashboard</h1>
            <p>Infrastructure setup and monitoring for multi-agent documentation system</p>
          </div>
          <button
            onClick={fetchServicesStatus}
            className={styles.refreshButton}
          >
            <RefreshCw className={styles.refreshIcon} />
            Refresh
          </button>
        </div>

        {/* System Overview */}
        <div className={styles.overviewCard}>
          <div className={styles.cardHeader}>
            <h2>System Overview</h2>
          </div>
          <div className={styles.cardBody}>
            <div className={styles.statsGrid}>
              <div className={`${styles.statCard} ${styles.gray}`}>
                <div className={styles.statContent}>
                  <Activity className={`${styles.statIcon} ${styles.gray}`} />
                  <div className={styles.statData}>
                    <dt>Total Services</dt>
                    <dd className={styles.gray}>{totalServices}</dd>
                  </div>
                </div>
              </div>

              <div className={`${styles.statCard} ${styles.green}`}>
                <div className={styles.statContent}>
                  <Server className={`${styles.statIcon} ${styles.green}`} />
                  <div className={styles.statData}>
                    <dt className={styles.green}>Healthy</dt>
                    <dd className={styles.green}>{healthyServices}</dd>
                  </div>
                </div>
              </div>

              <div className={`${styles.statCard} ${styles.yellow}`}>
                <div className={styles.statContent}>
                  <AlertCircle className={`${styles.statIcon} ${styles.yellow}`} />
                  <div className={styles.statData}>
                    <dt className={styles.yellow}>Degraded</dt>
                    <dd className={styles.yellow}>{degradedServices}</dd>
                  </div>
                </div>
              </div>

              <div className={`${styles.statCard} ${styles.blue}`}>
                <div className={styles.statContent}>
                  <Database className={`${styles.statIcon} ${styles.blue}`} />
                  <div className={styles.statData}>
                    <dt className={styles.blue}>Avg Response</dt>
                    <dd className={styles.blue}>{avgResponseTime}ms</dd>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Service Status Grid */}
        <div className={styles.servicesGrid}>
          {services.map((service) => (
            <div key={service.name} className={styles.serviceCard}>
              <div className={styles.serviceHeader}>
                <div className={styles.serviceInfo}>
                  {React.cloneElement(service.icon as React.ReactElement, {
                    className: styles.serviceIcon
                  })}
                  <h3 className={styles.serviceName}>{service.name}</h3>
                </div>
                <div className={styles.responseTime}>
                  {service.responseTime}ms
                </div>
              </div>
              <div className={styles.serviceDetails}>
                <p className={styles.serviceEndpoint}>{getEndpointFromService(service.name)}</p>
                <div className={`${styles.serviceStatus} ${styles[service.status]}`}>
                  {service.status === 'healthy' ? 'Service operational' :
                   service.status === 'degraded' ? 'Performance issues' :
                   'Server disconnected'}
                </div>
                <p className={styles.serviceTimestamp}>
                  Last checked: {new Date(service.lastCheck).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Dashboard