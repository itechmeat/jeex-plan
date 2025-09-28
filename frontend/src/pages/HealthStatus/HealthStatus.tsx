import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  Globe,
  Layers,
  RefreshCw,
  Server,
  XCircle,
  Zap,
} from 'lucide-react';
import React from 'react';
import { healthUtils, useHealthStatus } from '../../hooks/useHealthStatus';
import type { HealthCheck } from '../../services/healthService';
import styles from './HealthStatus.module.css';

const ICON_MAP = {
  api: Activity,
  database: Database,
  cache: Zap,
  queue: Layers,
  frontend: Globe,
  other: Server,
} as const;

const STATUS_ICON_MAP = {
  pass: CheckCircle2,
  warn: AlertTriangle,
  fail: XCircle,
  unknown: AlertCircle,
} as const;

const HEALTH_STATUS_TEXTS = {
  description: 'Real-time monitoring of JEEX Plan infrastructure components',
  extendedDescription:
    'Real-time monitoring of JEEX Plan infrastructure components with automatic updates every 30 seconds',
  noServicesMessage:
    'No health check data is currently available. The system may be initializing.',
} as const;

interface ServiceCardProps {
  service: HealthCheck;
  index: number;
}

function ServiceCard({ service, index }: ServiceCardProps) {
  const serviceType = healthUtils.getServiceType(service.service);
  const ServiceIcon = ICON_MAP[serviceType];

  return (
    <div
      className={`${styles.serviceCard} ${styles[service.status]}`}
      style={{ '--card-index': index } as React.CSSProperties}
    >
      <div className={styles.serviceHeader}>
        <div className={styles.serviceInfo}>
          <div className={`${styles.serviceIcon} ${styles[serviceType]}`}>
            <ServiceIcon size={24} />
          </div>
          <h3 className={styles.serviceName}>{service.service}</h3>
        </div>
        <div className={styles.responseTime}>
          {healthUtils.formatResponseTime(service.responseTime)}
        </div>
      </div>

      <div className={styles.serviceBody}>
        <div className={styles.endpoint}>{service.endpoint}</div>

        <div className={`${styles.status} ${styles[service.status]}`}>
          {service.status === 'pass' && 'Operational'}
          {service.status === 'warn' && 'Performance Issues'}
          {service.status === 'fail' && 'Service Unavailable'}
        </div>

        <div className={`${styles.details} ${styles[service.status]}`}>
          {service.details}
        </div>

        <div className={styles.serviceFooter}>
          <p className={styles.timestamp}>
            <Clock size={12} />
            {new Date(service.timestamp).toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
          {service.uptime != null && (
            <div className={styles.uptime}>
              Up: {healthUtils.formatUptime(service.uptime)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface StatusBannerProps {
  status: 'pass' | 'warn' | 'fail' | 'unknown';
  totalServices: number;
  healthyServices: number;
  warningServices: number;
  failedServices: number;
  lastUpdated?: string;
}

function StatusBanner({
  status,
  totalServices,
  healthyServices,
  warningServices,
  failedServices,
  lastUpdated,
}: StatusBannerProps) {
  const StatusIcon = STATUS_ICON_MAP[status];
  const message = healthUtils.getStatusMessage(status);

  return (
    <div className={`${styles.statusBanner} ${styles[status]}`}>
      <div className={styles.statusBannerContent}>
        <div className={styles.statusInfo}>
          <div className={`${styles.statusIcon} ${styles[status]}`}>
            <StatusIcon size={24} />
          </div>
          <div className={styles.statusDetails}>
            <h2>{message}</h2>
            <p>
              {status === 'pass'
                ? `All ${totalServices} services are running smoothly`
                : `${healthyServices}/${totalServices} services operational`}
              {lastUpdated &&
                ` • Last updated ${new Date(lastUpdated).toLocaleTimeString()}`}
            </p>
          </div>
        </div>

        <div className={styles.statusMetrics}>
          <div className={styles.metric}>
            <div className={`${styles.value} ${styles.success}`}>{healthyServices}</div>
            <p className={styles.label}>Healthy</p>
          </div>
          {warningServices > 0 && (
            <div className={styles.metric}>
              <div className={`${styles.value} ${styles.warning}`}>
                {warningServices}
              </div>
              <p className={styles.label}>Warning</p>
            </div>
          )}
          {failedServices > 0 && (
            <div className={styles.metric}>
              <div className={`${styles.value} ${styles.error}`}>{failedServices}</div>
              <p className={styles.label}>Failed</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface LoadingStateProps {
  message?: string;
}

function LoadingState({
  message = 'Loading system health status...',
}: LoadingStateProps) {
  return (
    <div className={styles.loading}>
      <div className={styles.loadingIcon} />
      <span>{message}</span>
    </div>
  );
}

interface ErrorStateProps {
  error: Error;
  onRetry: () => void;
}

function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className={styles.errorState}>
      <AlertCircle className={styles.errorIcon} />
      <div>
        <h3>Failed to load system health</h3>
        <p className={styles.errorMessage}>
          {error.message ||
            'An unexpected error occurred while fetching system health status.'}
        </p>
        <button
          className={styles.refreshButton}
          onClick={onRetry}
          aria-label='Retry loading health status'
        >
          <RefreshCw size={20} />
        </button>
      </div>
    </div>
  );
}

export default function HealthStatus() {
  const { data: healthData, isLoading, error, refetch, isFetching } = useHealthStatus();

  const handleRefresh = React.useCallback(() => {
    refetch();
  }, [refetch]);

  // Handle keyboard shortcut for refresh
  React.useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.key === 'r' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        handleRefresh();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handleRefresh]);

  if (isLoading) {
    return (
      <div className={styles.healthStatus}>
        <div className={styles.container}>
          <div className={styles.header}>
            <h1>System Health Status</h1>
            <p>{HEALTH_STATUS_TEXTS.description}</p>
          </div>
          <LoadingState />
        </div>
      </div>
    );
  }

  if (error && !healthData) {
    return (
      <div className={styles.healthStatus}>
        <div className={styles.container}>
          <div className={styles.header}>
            <h1>System Health Status</h1>
            <p>{HEALTH_STATUS_TEXTS.description}</p>
          </div>
          <ErrorState error={error as Error} onRetry={handleRefresh} />
        </div>
      </div>
    );
  }

  const services = healthData?.services || [];
  const overall = healthData?.overall || {
    status: 'unknown' as const,
    totalServices: services.length,
    healthyServices: services.filter(s => s.status === 'pass').length,
    warningServices: services.filter(s => s.status === 'warn').length,
    failedServices: services.filter(s => s.status === 'fail').length,
    lastUpdated: new Date().toISOString(),
  };

  return (
    <div className={styles.healthStatus}>
      <div className={styles.container}>
        <header className={styles.header}>
          <h1>System Health Status</h1>
          <p>{HEALTH_STATUS_TEXTS.extendedDescription}</p>
        </header>

        <StatusBanner
          status={overall.status}
          totalServices={overall.totalServices}
          healthyServices={overall.healthyServices}
          warningServices={overall.warningServices}
          failedServices={overall.failedServices}
          lastUpdated={overall.lastUpdated}
        />

        {services.length > 0 ? (
          <div className={styles.servicesGrid}>
            {services.map((service, index) => (
              <ServiceCard key={service.service} service={service} index={index} />
            ))}
          </div>
        ) : (
          <div className={styles.errorState}>
            <Server className={styles.errorIcon} />
            <div>
              <h3>No services found</h3>
              <p className={styles.errorMessage}>
                {HEALTH_STATUS_TEXTS.noServicesMessage}
              </p>
            </div>
          </div>
        )}

        <button
          className={styles.refreshButton}
          onClick={handleRefresh}
          disabled={isFetching}
          title='Refresh health status (Ctrl/Cmd + R)'
          aria-label='Refresh system health status'
        >
          <RefreshCw
            className={`${styles.refreshIcon} ${isFetching ? styles.spinning : ''}`}
            size={20}
          />
        </button>
      </div>
    </div>
  );
}
