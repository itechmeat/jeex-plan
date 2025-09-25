import { createCollection } from '@tanstack/react-db';
import { healthService } from '../services/healthService';

// Health Status collection record type
export interface HealthStatusRecord {
  id: string;
  service: string;
  endpoint: string;
  status: 'pass' | 'fail' | 'warn';
  responseTime: number;
  details: string;
  timestamp: string;
  version?: string;
  uptime?: number;
}

// System metrics record type
export interface SystemMetricsRecord {
  id: string;
  status: 'pass' | 'fail' | 'warn' | 'unknown';
  totalServices: number;
  healthyServices: number;
  warningServices: number;
  failedServices: number;
  lastUpdated: string;
}

// Create health status collection with REST API sync
const generateHealthRecordId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  // Fallback uses timestamp plus random segment to reduce collision risk
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

export const healthStatusCollection = createCollection<HealthStatusRecord>({
  id: 'healthStatus',
  getKey: record => record.id,
  sync: {
    sync: async ({ begin, write, commit, markReady, truncate }) => {
      try {
        begin();

        // Fetch health data from API
        const systemHealth = await healthService.getSystemHealth();

        // Transform services into health status records
        const healthRecords: HealthStatusRecord[] = systemHealth.services.map(
          service => ({
            id: `${service.service}-${generateHealthRecordId()}`,
            service: service.service,
            endpoint: service.endpoint,
            status: service.status,
            responseTime: service.responseTime,
            details: service.details,
            timestamp: service.timestamp,
            version: service.version,
            uptime: service.uptime,
          })
        );

        // Clear existing data and insert new records
        truncate();

        // Write all health records
        healthRecords.forEach(record => {
          write({
            type: 'insert',
            value: record,
          });
        });

        commit();
        markReady();
      } catch (error) {
        console.error('Health status sync error:', error);
        throw error;
      }
    },
  },
});

// Create system metrics collection
export const systemMetricsCollection = createCollection<SystemMetricsRecord>({
  id: 'systemMetrics',
  getKey: record => record.id,
  sync: {
    sync: async ({ begin, write, commit, markReady, truncate }) => {
      try {
        begin();

        // Fetch health data from API
        const systemHealth = await healthService.getSystemHealth();

        // Create system metrics record
        const metricsRecord: SystemMetricsRecord = {
          id: 'current-metrics',
          status: systemHealth.overall.status,
          totalServices: systemHealth.overall.totalServices,
          healthyServices: systemHealth.overall.healthyServices,
          warningServices: systemHealth.overall.warningServices,
          failedServices: systemHealth.overall.failedServices,
          lastUpdated: systemHealth.overall.lastUpdated,
        };

        // Clear existing data and insert new record
        truncate();

        // Write metrics record
        write({
          type: 'insert',
          value: metricsRecord,
        });

        commit();
        markReady();
      } catch (error) {
        console.error('System metrics sync error:', error);
        throw error;
      }
    },
  },
});

// Collections registry for easy access
export const collections = {
  healthStatus: healthStatusCollection,
  systemMetrics: systemMetricsCollection,
} as const;
