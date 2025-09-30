import { defineConfig, devices } from "@playwright/test";

// Helper function to safely parse integer environment variables
function parseEnvInt(name: string, defaultValue: number): number {
  const value = process.env[name];
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    throw new Error(
      `Invalid environment variable ${name}: "${value}" is not a valid integer. Expected a number, got "${value}".`
    );
  }
  return parsed;
}

// Helper function to validate Playwright option values against allowed values
function validatePlaywrightOption<T extends string>(
  name: string,
  value: string | undefined,
  allowedValues: readonly T[],
  defaultValue: T
): T {
  if (!value) return defaultValue;
  if (allowedValues.includes(value as T)) return value as T;
  throw new Error(
    `Invalid environment variable ${name}: "${value}" is not allowed. Must be one of: ${allowedValues.join(", ")}`
  );
}

// Allowed values for Playwright options
const TRACE_OPTIONS = ["on", "off", "on-first-retry", "on-all-retries", "retain-on-failure"] as const;
const SCREENSHOT_OPTIONS = ["off", "on", "only-on-failure"] as const;
const VIDEO_OPTIONS = ["off", "on", "retain-on-failure", "on-first-retry"] as const;

// Allowed backend commands to prevent command injection
// Note: This is a test configuration. Only these commands are allowed for security.
const ALLOWED_BACKEND_COMMANDS = [
  "cd .. && make up",
  "cd .. && make dev",
  "cd .. && make test-backend",
  "docker-compose up -d",
] as const;

function validateBackendCommand(command: string | undefined): string {
  const defaultCommand = "cd .. && make up";
  if (!command) return defaultCommand;

  if (ALLOWED_BACKEND_COMMANDS.includes(command as (typeof ALLOWED_BACKEND_COMMANDS)[number])) {
    return command;
  }

  throw new Error(
    `Invalid BACKEND_COMMAND: "${command}" is not in the allowlist. This prevents command injection attacks. ` +
      `Allowed commands: ${ALLOWED_BACKEND_COMMANDS.join(", ")}`
  );
}

// Configuration constants with environment variable fallbacks and validation
const TEST_CONFIG = {
  RETRIES_CI: parseEnvInt("PLAYWRIGHT_RETRIES_CI", 2),
  RETRIES_LOCAL: parseEnvInt("PLAYWRIGHT_RETRIES_LOCAL", 0),
  WORKERS_CI: parseEnvInt("PLAYWRIGHT_WORKERS_CI", 1),
  FRONTEND_PORT: parseEnvInt("FRONTEND_PORT", 5200),
  BACKEND_PORT: parseEnvInt("BACKEND_PORT", 5210),
  HOST: process.env.TEST_HOST || "127.0.0.1",
  FRONTEND_TIMEOUT: parseEnvInt("FRONTEND_TIMEOUT", 120000),
  BACKEND_TIMEOUT: parseEnvInt("BACKEND_TIMEOUT", 180000),
  BASE_URL:
    process.env.PLAYWRIGHT_BASE_URL ||
    `http://${process.env.TEST_HOST || "127.0.0.1"}:${parseEnvInt("FRONTEND_PORT", 5200)}`,
  BACKEND_COMMAND: validateBackendCommand(process.env.BACKEND_COMMAND),
  TRACE: validatePlaywrightOption("PLAYWRIGHT_TRACE", process.env.PLAYWRIGHT_TRACE, TRACE_OPTIONS, "on-first-retry"),
  SCREENSHOT: validatePlaywrightOption(
    "PLAYWRIGHT_SCREENSHOT",
    process.env.PLAYWRIGHT_SCREENSHOT,
    SCREENSHOT_OPTIONS,
    "only-on-failure"
  ),
  VIDEO: validatePlaywrightOption("PLAYWRIGHT_VIDEO", process.env.PLAYWRIGHT_VIDEO, VIDEO_OPTIONS, "retain-on-failure"),
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: Number(process.env.PW_RETRIES ?? (process.env.CI ? TEST_CONFIG.RETRIES_CI : TEST_CONFIG.RETRIES_LOCAL)),
  workers: process.env.CI
    ? TEST_CONFIG.WORKERS_CI
    : process.env.PW_WORKERS
    ? Number(process.env.PW_WORKERS)
    : undefined,

  reporter: [
    ["html", { outputFolder: process.env.PLAYWRIGHT_HTML_REPORT || "playwright-report" }],
    ["json", { outputFile: process.env.PLAYWRIGHT_JSON_REPORT || "test-results/results.json" }],
    ["junit", { outputFile: process.env.PLAYWRIGHT_JUNIT_REPORT || "test-results/results.xml" }],
  ],

  use: {
    baseURL: TEST_CONFIG.BASE_URL,
    trace: TEST_CONFIG.TRACE,
    screenshot: TEST_CONFIG.SCREENSHOT,
    video: TEST_CONFIG.VIDEO,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],

  // Global setup and teardown
  globalSetup: "./setup/global-setup.ts",
  globalTeardown: "./setup/global-teardown.ts",

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
      command: TEST_CONFIG.BACKEND_COMMAND,
      url: `http://${TEST_CONFIG.HOST}:${TEST_CONFIG.BACKEND_PORT}`,
      timeout: TEST_CONFIG.BACKEND_TIMEOUT,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
