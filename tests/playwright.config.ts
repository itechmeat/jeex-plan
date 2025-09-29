import { defineConfig, devices } from '@playwright/test';

// Configuration constants with environment variable fallbacks
const TEST_CONFIG = {
  RETRIES_CI: parseInt(process.env.PLAYWRIGHT_RETRIES_CI || '2', 10),
  RETRIES_LOCAL: parseInt(process.env.PLAYWRIGHT_RETRIES_LOCAL || '0', 10),
  WORKERS_CI: parseInt(process.env.PLAYWRIGHT_WORKERS_CI || '1', 10),
  FRONTEND_PORT: parseInt(process.env.FRONTEND_PORT || '5200', 10),
  BACKEND_PORT: parseInt(process.env.BACKEND_PORT || '5210', 10),
  HOST: process.env.TEST_HOST || '127.0.0.1',
  FRONTEND_TIMEOUT: parseInt(process.env.FRONTEND_TIMEOUT || '120000', 10),
  BACKEND_TIMEOUT: parseInt(process.env.BACKEND_TIMEOUT || '180000', 10),
  BASE_URL: process.env.PLAYWRIGHT_BASE_URL || `http://${process.env.TEST_HOST || '127.0.0.1'}:${process.env.FRONTEND_PORT || '5200'}`,
};

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: Number(process.env.PW_RETRIES ?? (process.env.CI ? TEST_CONFIG.RETRIES_CI : TEST_CONFIG.RETRIES_LOCAL)),
  workers: process.env.CI
    ? TEST_CONFIG.WORKERS_CI
    : (process.env.PW_WORKERS ? Number(process.env.PW_WORKERS) : undefined),

  reporter: [
    ['html', { outputFolder: process.env.PLAYWRIGHT_HTML_REPORT || 'playwright-report' }],
    ['json', { outputFile: process.env.PLAYWRIGHT_JSON_REPORT || 'test-results/results.json' }],
    ['junit', { outputFile: process.env.PLAYWRIGHT_JUNIT_REPORT || 'test-results/results.xml' }]
  ],

  use: {
    baseURL: TEST_CONFIG.BASE_URL,
    trace: (process.env.PLAYWRIGHT_TRACE as 'on' | 'off' | 'on-first-retry' | 'on-all-retries' | 'retain-on-failure') || 'on-first-retry',
    screenshot: (process.env.PLAYWRIGHT_SCREENSHOT as 'off' | 'on' | 'only-on-failure') || 'only-on-failure',
    video: (process.env.PLAYWRIGHT_VIDEO as 'off' | 'on' | 'retain-on-failure' | 'on-first-retry') || 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // Global setup and teardown
  globalSetup: './setup/global-setup.ts',
  globalTeardown: './setup/global-teardown.ts',

  webServer: [
    {
      command: process.env.CI
        ? `cd ../frontend && pnpm run preview -- --port ${TEST_CONFIG.FRONTEND_PORT} --host ${TEST_CONFIG.HOST}`
        : `cd ../frontend && pnpm run dev -- --port ${TEST_CONFIG.FRONTEND_PORT} --host ${TEST_CONFIG.HOST}`,
      url: `http://${TEST_CONFIG.HOST}:${TEST_CONFIG.FRONTEND_PORT}`,
      timeout: TEST_CONFIG.FRONTEND_TIMEOUT,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: process.env.BACKEND_COMMAND || 'cd .. && make up',
      url: `http://${TEST_CONFIG.HOST}:${TEST_CONFIG.BACKEND_PORT}`,
      timeout: TEST_CONFIG.BACKEND_TIMEOUT,
      reuseExistingServer: !process.env.CI,
    },
  ],
});