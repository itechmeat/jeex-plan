import { chromium, FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('🧹 Cleaning up test environment...');

  // Clean up test data
  try {
    const cleanupResponse = await page.request.post('http://localhost:5210/api/v1/test/cleanup', {
      headers: { 'Content-Type': 'application/json' }
    });
    if (cleanupResponse.ok()) {
      console.log('✅ Test data cleaned');
    }
  } catch (error) {
    console.log('⚠️  Could not clean test data');
  }

  await context.close();
  await browser.close();

  console.log('✅ Test environment cleaned');
}

export default globalTeardown;