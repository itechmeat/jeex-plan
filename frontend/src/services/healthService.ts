import { apiClient } from './api';

export interface HealthCheck {
  service: string;
  endpoint: string;
  status: 'pass' | 'fail' | 'warn';
  responseTime: number;
  details: string;
  timestamp: string;
  version?: string;
  uptime?: number;
}

export interface SystemHealthResponse {
  status: 'pass' | 'fail' | 'warn';
  services: HealthCheck[];
  overall: {
    status: 'pass' | 'fail' | 'warn';
    totalServices: number;
    healthyServices: number;
    warningServices: number;
    failedServices: number;
    lastUpdated: string;
  };
}

export const healthService = {
  /**
   * Fetches comprehensive system health status
   * @returns Promise with system health data
   */
  async getSystemHealth(): Promise<SystemHealthResponse> {
    try {
      const healthData = await apiClient.getHealthStatus();

      // Transform to our expected format if needed
      return {
        status: (healthData.status as 'pass' | 'fail' | 'warn') || 'fail',
        services: healthData.services || [],
        overall: healthData.overall || {
          status: (healthData.status as 'pass' | 'fail' | 'warn') || 'fail',
          totalServices: healthData.services?.length || 0,
          healthyServices:
            healthData.services?.filter(s => s.status === 'pass').length || 0,
          warningServices:
            healthData.services?.filter(s => s.status === 'warn').length || 0,
          failedServices:
            healthData.services?.filter(s => s.status === 'fail').length || 0,
          lastUpdated: new Date().toISOString(),
        },
      };
    } catch (error) {
      console.error('Failed to fetch system health:', error);

      // Return fallback response for error cases
      const timestamp = new Date().toISOString();
      return {
        status: 'fail',
        overall: {
          status: 'fail',
          totalServices: 1,
          healthyServices: 0,
          warningServices: 0,
          failedServices: 1,
          lastUpdated: timestamp,
        },
        services: [
          {
            service: 'System Status',
            endpoint: '/health',
            status: 'fail',
            responseTime: 0,
            details: `Failed to load system health: ${error instanceof Error ? error.message : 'Unknown error'}`,
            timestamp,
          },
        ],
      };
    }
  },

  /**
   * Fetches health status for a specific service
   * @param serviceName - Name of the service to check
   * @returns Promise with service health data
   */
  async getServiceHealth(serviceName: string): Promise<HealthCheck> {
    try {
      // For now, we'll get the full health status and filter for the specific service
      const systemHealth = await this.getSystemHealth();
      const serviceHealth = systemHealth.services.find(s =>
        s.service.toLowerCase().includes(serviceName.toLowerCase())
      );

      if (serviceHealth) {
        return serviceHealth;
      }

      // Service not found, return a "not found" status
      return {
        service: serviceName,
        endpoint: `/health/${serviceName}`,
        status: 'fail',
        responseTime: 0,
        details: `Service '${serviceName}' not found in health status`,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      console.error(`Failed to fetch health for service ${serviceName}:`, error);

      return {
        service: serviceName,
        endpoint: `/health/${serviceName}`,
        status: 'fail',
        responseTime: 0,
        details: `Failed to load service health: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
    }
  },
};
