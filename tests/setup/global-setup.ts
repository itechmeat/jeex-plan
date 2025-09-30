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
  });

  console.log("🚀 Setting up test environment...");
  console.log(`📍 Backend URL: ${backendBaseURL}`);
  console.log(`📍 Frontend URL: ${frontendBaseURL}`);

  try {
    // Wait for backend to be ready
    await waitForService(
      apiContext,
      `${backendBaseURL}/api/v1/health`,
      "Backend",
      SETUP_CONFIG.MAX_RETRIES,
      SETUP_CONFIG.INITIAL_DELAY_MS,
      5000
    );

    // Wait for frontend to be ready
    await waitForService(
      apiContext,
      frontendBaseURL,
      "Frontend",
      SETUP_CONFIG.MAX_RETRIES,
      SETUP_CONFIG.INITIAL_DELAY_MS,
      5000
    );

    // Clean up test data if needed
    try {
      console.log("🧹 Cleaning up test data...");
      const cleanupResponse = await apiContext.post(`${backendBaseURL}/api/v1/test/cleanup`, {
        headers: { "Content-Type": "application/json" },
        timeout: SETUP_CONFIG.REQUEST_TIMEOUT,
      });

      if (cleanupResponse.ok()) {
        console.log("🧹 Test data cleaned successfully");
      } else {
        console.log(`⚠️ Cleanup returned status ${cleanupResponse.status()} (may be expected)`);
      }
    } catch (error) {
      console.log("⚠️ Could not clean test data (endpoint might not exist)");
    }

    console.log("✅ Test environment ready");
  } finally {
    // Always dispose of the API context
    await apiContext.dispose();
  }
}

export default globalSetup;
