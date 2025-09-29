import { request, FullConfig } from '@playwright/test';

// Configuration constants with environment variable fallbacks
const TEARDOWN_CONFIG = {
  BACKEND_HOST: process.env.TEST_HOST || '127.0.0.1',
  BACKEND_PORT: parseInt(process.env.BACKEND_PORT || '5210', 10),
  REQUEST_TIMEOUT: parseInt(process.env.CLEANUP_TIMEOUT || '15000', 10),
  MAX_RETRIES: parseInt(process.env.CLEANUP_RETRIES || '3', 10),
};

async function globalTeardown(config: FullConfig) {
  const baseURL = process.env.E2E_API_BASE_URL ||
                  process.env.PLAYWRIGHT_BASE_URL ||
                  `http://${TEARDOWN_CONFIG.BACKEND_HOST}:${TEARDOWN_CONFIG.BACKEND_PORT}`;

  const apiContext = await request.newContext({
    baseURL,
    timeout: TEARDOWN_CONFIG.REQUEST_TIMEOUT,
    ignoreHTTPSErrors: true
  });

  console.log('🧹 Cleaning up test environment...');

  // Clean up test data with improved error handling
  try {
    const res = await apiContext.post('/api/v1/test/cleanup', {
      headers: { 'Content-Type': 'application/json' },
    });

    if (res.ok()) {
      console.log('✅ Test data cleaned successfully');
    } else {
      console.warn(`⚠️ Cleanup failed: ${res.status()} ${res.statusText()}`);
      try {
        const responseText = await res.text();
        if (responseText.trim()) {
          console.warn(`Response: ${responseText}`);
        }
      } catch {
        // Ignore text parsing errors
      }
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.warn('⚠️ Could not clean test data:', errorMessage);
  } finally {
    // Always dispose of the API context
    await apiContext.dispose();
  }

  console.log('✅ Test environment cleanup completed');
}

export default globalTeardown;