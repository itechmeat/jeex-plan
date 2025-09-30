import { request, FullConfig, APIRequestContext } from "@playwright/test";

// Configuration constants with environment variable fallbacks
const SETUP_CONFIG = {
  BACKEND_HOST: process.env.TEST_HOST || "127.0.0.1",
  BACKEND_PORT: parseInt(process.env.BACKEND_PORT || "5210", 10),
  FRONTEND_PORT: parseInt(process.env.FRONTEND_PORT || "5200", 10),
  REQUEST_TIMEOUT: parseInt(process.env.SETUP_TIMEOUT || "10000", 10),
  MAX_RETRIES: parseInt(process.env.SETUP_RETRIES || "30", 10),
  INITIAL_DELAY_MS: 1000,
};

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
  apiContext: APIRequestContext,
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
        ignoreHTTPSErrors: true,
      });

      if (response.ok()) {
        console.log(`✅ ${serviceName} is ready (status: ${response.status()})`);
        return;
      }

      // Non-OK response - log status and continue retrying
      console.log(`❌ ${serviceName} returned status ${response.status()}, retrying...`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      console.log(`❌ ${serviceName} connection failed: ${errorMessage}, retrying...`);
    }

    // Always decrement retries and wait (fixing busy-loop bug)
    retries--;

    if (retries > 0) {
      console.log(`⏳ Waiting ${delay}ms before next ${serviceName} attempt...`);
      await new Promise((resolve) => setTimeout(resolve, delay));

      // Exponential backoff with cap
      delay = Math.min(delay * 1.2, 5000);
    }
  }

  throw new Error(`❌ ${serviceName} failed to start in time after ${maxRetries} attempts`);
}

async function globalSetup(config: FullConfig) {
  // Build base URLs from configuration
  const backendBaseURL = `http://${SETUP_CONFIG.BACKEND_HOST}:${SETUP_CONFIG.BACKEND_PORT}`;
  const frontendBaseURL = `http://${SETUP_CONFIG.BACKEND_HOST}:${SETUP_CONFIG.FRONTEND_PORT}`;

  // Use APIRequestContext instead of full browser (faster, less resource usage)
  const apiContext = await request.newContext({
    // Global request settings
    timeout: SETUP_CONFIG.REQUEST_TIMEOUT,
    ignoreHTTPSErrors: true,
    extraHTTPHeaders: {
      "Content-Type": "application/json",
    },
  });

  console.log("🚀 Setting up test environment...");
  console.log(`📍 Backend URL: ${backendBaseURL}`);
  console.log(`📍 Frontend URL: ${frontendBaseURL}`);

  try {
    // Wait for backend to be ready
    console.log("⏳ Waiting for backend service...");
    await waitForService(
      apiContext,
      `${backendBaseURL}/api/v1/health`,
      "Backend",
      SETUP_CONFIG.MAX_RETRIES,
      SETUP_CONFIG.INITIAL_DELAY_MS,
      5000
    );

    // Verify backend health details
    console.log("🔍 Verifying backend health details...");
    const healthResponse = await apiContext.get(`${backendBaseURL}/api/v1/health`);
    if (healthResponse.ok()) {
      const health = await healthResponse.json();
      console.log("✅ Backend health check passed:");
      console.log(`   - Status: ${health.status}`);
      console.log(`   - Database: ${health.components?.database?.status || 'unknown'}`);
      console.log(`   - Redis: ${health.components?.redis?.status || 'unknown'}`);
      console.log(`   - Qdrant: ${health.components?.qdrant?.status || 'unknown'}`);
      console.log(`   - Vault: ${health.components?.vault?.status || 'unknown'}`);
    }

    // Wait for frontend to be ready
    console.log("⏳ Waiting for frontend service...");
    await waitForService(
      apiContext,
      frontendBaseURL,
      "Frontend",
      SETUP_CONFIG.MAX_RETRIES,
      SETUP_CONFIG.INITIAL_DELAY_MS,
      5000
    );

    // Test CORS preflight request
    console.log("🔍 Testing CORS preflight...");
    try {
      const corsResponse = await apiContext.fetch(`${backendBaseURL}/api/v1/auth/login`, {
        method: "OPTIONS",
        headers: {
          "Origin": `http://${SETUP_CONFIG.BACKEND_HOST}:${SETUP_CONFIG.FRONTEND_PORT}`,
          "Access-Control-Request-Method": "POST",
          "Access-Control-Request-Headers": "Content-Type",
        },
      });

      if (corsResponse.ok()) {
        console.log("✅ CORS preflight request successful");
      } else {
        console.log(`⚠️ CORS preflight returned status ${corsResponse.status()}`);
      }
    } catch (error) {
      console.log(`⚠️ CORS preflight test failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }

    // Clean up test data if needed
    console.log("🧹 Cleaning up test data...");
    try {
      const cleanupResponse = await apiContext.post(`${backendBaseURL}/api/v1/test/cleanup`, {
        headers: { "Content-Type": "application/json" },
        timeout: SETUP_CONFIG.REQUEST_TIMEOUT,
      });

      if (cleanupResponse.ok()) {
        const result = await cleanupResponse.json();
        console.log(`🧹 Test data cleaned successfully: ${result.message}`);
      } else {
        console.log(`⚠️ Cleanup returned status ${cleanupResponse.status()}`);
        if (cleanupResponse.status() === 404) {
          console.log("   (This is expected if test endpoint is not implemented)");
        }
      }
    } catch (error) {
      console.log(`⚠️ Could not clean test data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }

    console.log("✅ Test environment ready for E2E testing");

    // Store configuration for global teardown
    process.env.E2E_BACKEND_URL = backendBaseURL;
    process.env.E2E_FRONTEND_URL = frontendBaseURL;

  } catch (error) {
    console.error("❌ E2E setup failed:", error instanceof Error ? error.message : 'Unknown error');
    throw error;
  } finally {
    // Always dispose of the API context
    await apiContext.dispose();
  }
}

export default globalSetup;
