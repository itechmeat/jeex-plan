import type { HealthCheck, SystemHealthResponse } from '../types/api';
import { apiClient } from './api';

export const healthService = {
  /**
   * Fetches comprehensive system health status
   * @returns Promise with system health data
   */
  async getSystemHealth(): Promise<SystemHealthResponse> {
    try {
      const healthData = await apiClient.getHealthStatus();

      const services: HealthCheck[] = healthData.services ?? [];
      const normalizedStatus =
        (healthData.status as 'pass' | 'fail' | 'warn') ?? 'fail';
      const overall = healthData.overall ?? {
        status: normalizedStatus,
        totalServices: services.length,
        healthyServices: services.filter(s => s.status === 'pass').length,
        warningServices: services.filter(s => s.status === 'warn').length,
        failedServices: services.filter(s => s.status === 'fail').length,
        lastUpdated: new Date().toISOString(),
      };

      return {
        status: normalizedStatus,
        services,
        overall,
      };
    } catch (error) {
      console.error('Failed to fetch system health:', error);
      throw error;
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
      throw error;
    }
  },
};
