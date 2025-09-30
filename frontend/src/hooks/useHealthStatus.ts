import { useLiveQuery } from '@tanstack/react-db';
import React from 'react';
import { useCollections } from '../providers/useCollections';
import { type HealthCheck, type SystemHealthResponse } from '../services/healthService';

export const HEALTH_REFRESH_INTERVAL = 30000; // 30 seconds

/**
 * Hook for fetching and managing system health status using TanStack DB
 * @param options - Configuration options for the health status hook
 * @returns Health status data with loading, error states and refresh functionality
 */
export function useHealthStatus(options?: {
  refetchInterval?: number;
  enabled?: boolean;
}) {
  const collections = useCollections();
  const refetchInterval = options?.refetchInterval ?? HEALTH_REFRESH_INTERVAL;
  const enabled = options?.enabled ?? true;

  // Use live query for health status records
  const healthStatusQuery = useLiveQuery(collections.healthStatus);

  // Use live query for system metrics
  const systemMetricsQuery = useLiveQuery(collections.systemMetrics);

  // Auto-refresh interval - trigger collection sync
  React.useEffect(() => {
    if (!enabled || refetchInterval <= 0) return;

    const interval = setInterval(() => {
      // Manually trigger sync for both collections
      if (collections.healthStatus.status === 'ready') {
        collections.healthStatus.preload();
      }
      if (collections.systemMetrics.status === 'ready') {
        collections.systemMetrics.preload();
      }
    }, refetchInterval);

    return () => clearInterval(interval);
  }, [collections, refetchInterval, enabled]);

  // Transform data for component consumption
  const healthData = React.useMemo((): SystemHealthResponse | null => {
    if (!enabled) return null;

    const healthRecords = healthStatusQuery.data;
    const metricsRecords = systemMetricsQuery.data;

    if (!healthRecords || !metricsRecords || metricsRecords.length === 0) {
      return null;
    }

    const metricsRecord = metricsRecords[0]; // Only one metrics record

    // Transform health status records back to HealthCheck format
    const services: HealthCheck[] = Array.from(healthRecords).map(record => ({
      service: record.service,
      endpoint: record.endpoint,
      status: record.status,
      responseTime: record.responseTime,
      details: record.details,
      timestamp: record.timestamp,
      version: record.version,
      uptime: record.uptime,
    }));

    return {
      status: metricsRecord.status === 'unknown' ? 'fail' : metricsRecord.status,
      services,
      overall: {
        status: metricsRecord.status === 'unknown' ? 'fail' : metricsRecord.status,
        totalServices: metricsRecord.totalServices,
        healthyServices: metricsRecord.healthyServices,
        warningServices: metricsRecord.warningServices,
        failedServices: metricsRecord.failedServices,
        lastUpdated: metricsRecord.lastUpdated,
      },
    };
  }, [healthStatusQuery.data, systemMetricsQuery.data, enabled]);

  // Calculate combined loading state
  const isLoading =
    collections.healthStatus.status === 'loading' ||
    collections.systemMetrics.status === 'loading';
  const isFetching = isLoading;
  const isError =
    collections.healthStatus.status === 'error' ||
    collections.systemMetrics.status === 'error';

  // Manual refetch function
  const refetch = React.useCallback(async () => {
    await Promise.all([
      collections.healthStatus.preload(),
      collections.systemMetrics.preload(),
    ]);
  }, [collections]);

  return {
    data: enabled ? healthData : null,
    isLoading: enabled ? isLoading : false,
    error: enabled && isError ? new Error('Failed to load health data') : null,
    isFetching: enabled ? isFetching : false,
    refetch,
  };
}

/**
 * Hook for fetching specific service health status using TanStack DB
 * @param serviceName - Name of the service to check
 * @param options - Configuration options for the service health hook
 * @returns Service health data with loading, error states and refresh functionality
 */
export function useServiceHealth(
  serviceName: string,
  options?: {
    refetchInterval?: number;
    enabled?: boolean;
  }
) {
  const collections = useCollections();
  const refetchInterval = options?.refetchInterval ?? HEALTH_REFRESH_INTERVAL;
  const enabled = (options?.enabled ?? true) && !!serviceName;

  // Use live query with filter for specific service
  const serviceQuery = useLiveQuery(collections.healthStatus);

  // Filter for specific service data
  const serviceData = React.useMemo((): HealthCheck | null => {
    if (!enabled || !serviceName || !serviceQuery.data) return null;

    const serviceRecord = Array.from(serviceQuery.data).find(record =>
      record.service.toLowerCase().includes(serviceName.toLowerCase())
    );

    if (!serviceRecord) return null;

    return {
      service: serviceRecord.service,
      endpoint: serviceRecord.endpoint,
      status: serviceRecord.status,
      responseTime: serviceRecord.responseTime,
      details: serviceRecord.details,
      timestamp: serviceRecord.timestamp,
      version: serviceRecord.version,
      uptime: serviceRecord.uptime,
    };
  }, [serviceQuery.data, serviceName, enabled]);

  // Auto-refresh interval - trigger collection sync
  React.useEffect(() => {
    if (!enabled || !serviceName || refetchInterval <= 0) return;

    const interval = setInterval(() => {
      if (collections.healthStatus.status === 'ready') {
        collections.healthStatus.preload();
      }
    }, refetchInterval);

    return () => clearInterval(interval);
  }, [collections, refetchInterval, enabled, serviceName]);

  // Manual refetch function
  const refetch = React.useCallback(async () => {
    await collections.healthStatus.preload();
  }, [collections]);

  return {
    data: enabled && serviceName ? serviceData : null,
    isLoading: enabled ? collections.healthStatus.status === 'loading' : false,
    error:
      enabled && collections.healthStatus.status === 'error'
        ? new Error('Failed to load service health data')
        : null,
    isFetching: enabled ? collections.healthStatus.status === 'loading' : false,
    refetch,
  };
}

/**
 * Hook for getting cached health data from TanStack DB without API calls
 * @returns Cached health data from the local database
 */
export function useCachedHealthStatus() {
  const collections = useCollections();

  // Use live queries to get cached data
  const healthStatusQuery = useLiveQuery(collections.healthStatus);
  const systemMetricsQuery = useLiveQuery(collections.systemMetrics);

  // Transform cached data for component consumption
  const cachedData = React.useMemo((): SystemHealthResponse | null => {
    const healthRecords = healthStatusQuery.data;
    const metricsRecords = systemMetricsQuery.data;

    if (!healthRecords || !metricsRecords || metricsRecords.length === 0) {
      return null;
    }

    const metricsRecord = metricsRecords[0]; // Only one metrics record

    // Transform health status records back to HealthCheck format
    const services: HealthCheck[] = Array.from(healthRecords).map(record => ({
      service: record.service,
      endpoint: record.endpoint,
      status: record.status,
      responseTime: record.responseTime,
      details: record.details,
      timestamp: record.timestamp,
      version: record.version,
      uptime: record.uptime,
    }));

    return {
      status: metricsRecord.status === 'unknown' ? 'fail' : metricsRecord.status,
      services,
      overall: {
        status: metricsRecord.status === 'unknown' ? 'fail' : metricsRecord.status,
        totalServices: metricsRecord.totalServices,
        healthyServices: metricsRecord.healthyServices,
        warningServices: metricsRecord.warningServices,
        failedServices: metricsRecord.failedServices,
        lastUpdated: metricsRecord.lastUpdated,
      },
    };
  }, [healthStatusQuery.data, systemMetricsQuery.data]);

  return {
    data: cachedData,
    isLoading:
      collections.healthStatus.status === 'loading' ||
      collections.systemMetrics.status === 'loading',
  };
}

/**
 * Utility functions for health status processing
 */
export const healthUtils = {
  /**
   * Get overall system status based on service statuses
   */
  getOverallStatus(services: HealthCheck[]): 'pass' | 'warn' | 'fail' | 'unknown' {
    if (!services.length) return 'unknown';

    const hasFailures = services.some(service => service.status === 'fail');
    const hasWarnings = services.some(service => service.status === 'warn');

    if (hasFailures) return 'fail';
    if (hasWarnings) return 'warn';
    return 'pass';
  },

  /**
   * Get status message for display
   */
  getStatusMessage(status: string): string {
    // TODO: Consider implementing a proper localization system
    // Previously used react-i18next but was removed to reduce dependencies
    // For now, messages are hardcoded in English as per project requirements

    switch (status) {
      case 'pass':
        return 'All systems operational';
      case 'warn':
        return 'Some services have performance issues';
      case 'fail':
        return 'Critical system issues detected';
      default:
        return 'System status unknown';
    }
  },

  /**
   * Get service icon based on service name
   */
  getServiceType(
    serviceName: string
  ): 'api' | 'database' | 'cache' | 'queue' | 'frontend' | 'other' {
    const name = serviceName.toLowerCase();

    if (name.includes('api') || name.includes('backend') || name.includes('fastapi')) {
      return 'api';
    }
    if (
      name.includes('postgres') ||
      name.includes('database') ||
      name.includes('qdrant')
    ) {
      return 'database';
    }
    if (name.includes('redis') || name.includes('cache')) {
      return 'cache';
    }
    if (name.includes('queue') || name.includes('worker')) {
      return 'queue';
    }
    if (name.includes('frontend') || name.includes('web') || name.includes('ui')) {
      return 'frontend';
    }
    return 'other';
  },

  /**
   * Format response time for display
   */
  formatResponseTime(ms: number): string {
    if (ms === 0) return '--';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  },

  /**
   * Format uptime for display
   */
  formatUptime(seconds?: number): string {
    if (!seconds) return '--';

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
      return `${days}d ${hours}h`;
    }
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  },

  /**
   * Clear all cached health data from TanStack DB collections
   */
  async clearHealthCache(): Promise<void> {
    try {
      // Import collections statically since they're already imported above
      const { healthStatusCollection, systemMetricsCollection } = await import(
        '../providers/collections'
      );

      // Clear both collections by triggering cleanup
      await Promise.all([
        healthStatusCollection.cleanup(),
        systemMetricsCollection.cleanup(),
      ]);
    } catch (error) {
      console.error('Failed to clear health cache:', error);
      throw error;
    }
  },
};
