import { request, FullConfig } from '@playwright/test';

/**
 * Wait for a service to become ready with exponential backoff
 * @param apiContext APIRequestContext for making HTTP requests
 * @param url Service URL to check
 * @param serviceName Service name for logging
 * @param maxRetries Maximum number of retry attempts
 * @param initialDelayMs Initial delay between retries
 * @param timeoutMs Request timeout in milliseconds
 */
async function waitForService(
  apiContext: any,
  url: string,
  serviceName: string,
  maxRetries: number = 30,
  initialDelayMs: number = 1000,
  timeoutMs: number = 5000
): Promise<void> {
  let retries = maxRetries;
  let delay = initialDelayMs;

  while (retries > 0) {
    try {
      console.log(`⏳ Checking ${serviceName}... (${retries} retries left)`);

      const response = await apiContext.get(url, {
        timeout: timeoutMs,
        ignoreHTTPSErrors: true
      });

      if (response.ok()) {
        console.log(`✅ ${serviceName} is ready (status: ${response.status()})`);
        return;
      }

      // Non-OK response - log status and continue retrying
      console.log(`❌ ${serviceName} returned status ${response.status()}, retrying...`);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.log(`❌ ${serviceName} connection failed: ${errorMessage}, retrying...`);
    }

    // Always decrement retries and wait (fixing busy-loop bug)
    retries--;

    if (retries > 0) {
      console.log(`⏳ Waiting ${delay}ms before next ${serviceName} attempt...`);
      await new Promise(resolve => setTimeout(resolve, delay));

      // Exponential backoff with cap
      delay = Math.min(delay * 1.2, 5000);
    }
  }

  throw new Error(`❌ ${serviceName} failed to start in time after ${maxRetries} attempts`);
}

async function globalSetup(config: FullConfig) {
  // Use APIRequestContext instead of full browser (faster, less resource usage)
  const apiContext = await request.newContext({
    // Global request settings
    timeout: 10000,
    ignoreHTTPSErrors: true
  });

  console.log('🚀 Setting up test environment...');

  try {
    // Wait for backend to be ready
    await waitForService(
      apiContext,
      'http://localhost:5210/api/v1/health',
      'Backend',
      30,
      1000,
      5000
    );

    // Wait for frontend to be ready
    await waitForService(
      apiContext,
      'http://localhost:5200',
      'Frontend',
      30,
      1000,
      5000
    );

    // Clean up test data if needed
    try {
      console.log('🧹 Cleaning up test data...');
      const cleanupResponse = await apiContext.post('http://localhost:5210/api/v1/test/cleanup', {
        headers: { 'Content-Type': 'application/json' },
        timeout: 10000
      });

      if (cleanupResponse.ok()) {
        console.log('🧹 Test data cleaned successfully');
      } else {
        console.log(`⚠️ Cleanup returned status ${cleanupResponse.status()} (may be expected)`);
      }
    } catch (error) {
      console.log('⚠️ Could not clean test data (endpoint might not exist)');
    }

    console.log('✅ Test environment ready');

  } finally {
    // Always dispose of the API context
    await apiContext.dispose();
  }
}

export default globalSetup;