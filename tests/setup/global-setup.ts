import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('🚀 Setting up test environment...');

  // Wait for backend to be ready
  let retries = 30;
  while (retries > 0) {
    try {
      const response = await page.request.get('http://localhost:5210/api/v1/health');
      if (response.ok()) {
        console.log('✅ Backend is ready');
        break;
      }
    } catch (error) {
      console.log(`⏳ Waiting for backend... (${retries} retries left)`);
      await page.waitForTimeout(2000);
      retries--;
    }
  }

  if (retries === 0) {
    throw new Error('❌ Backend failed to start in time');
  }

  // Wait for frontend to be ready
  retries = 30;
  while (retries > 0) {
    try {
      const response = await page.request.get('http://localhost:5200');
      if (response.ok()) {
        console.log('✅ Frontend is ready');
        break;
      }
    } catch (error) {
      console.log(`⏳ Waiting for frontend... (${retries} retries left)`);
      await page.waitForTimeout(2000);
      retries--;
    }
  }

  if (retries === 0) {
    throw new Error('❌ Frontend failed to start in time');
  }

  // Clean up test data if needed
  try {
    const cleanupResponse = await page.request.post('http://localhost:5210/api/v1/test/cleanup', {
      headers: { 'Content-Type': 'application/json' }
    });
    if (cleanupResponse.ok()) {
      console.log('🧹 Test data cleaned');
    }
  } catch (error) {
    console.log('⚠️  Could not clean test data (might not exist)');
  }

  await context.close();
  await browser.close();

  console.log('✅ Test environment ready');
}

export default globalSetup;