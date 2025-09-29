import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['html', { outputFolder: 'test-results/html' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/results.xml' }]
  ],

  use: {
    baseURL: 'http://localhost:5200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
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

  // Web server configuration
  webServer: [
    {
      command: 'cd ../frontend && pnpm run dev',
      port: 5200,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd .. && make up',
      port: 5210,
      reuseExistingServer: !process.env.CI,
    }
  ],
});