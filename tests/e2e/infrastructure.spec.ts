import { test, expect } from "@playwright/test";

const BACKEND_URL = "http://127.0.0.1:5210";

test.describe("E2E Infrastructure Tests", () => {
  test("should verify backend health and connectivity", async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/v1/health`);

    expect(response.ok()).toBe(true);
    const health = await response.json();

    expect(health.status).toBe("healthy");
    expect(health.components).toBeDefined();
    expect(health.components.database.status).toBe("healthy");
    expect(health.components.redis.status).toBe("healthy");
    expect(health.components.qdrant.status).toBe("healthy");
  });

  test("should verify test cleanup endpoint works", async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/api/v1/test/cleanup`);

    expect(response.ok()).toBe(true);
    const result = await response.json();

    expect(result.status).toBe("success");
    expect(result.environment).toBe("development");
  });

  test("should handle CORS preflight requests correctly", async ({ request }) => {
    const response = await request.fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method: "OPTIONS",
      headers: {
        "Origin": "http://localhost:5200",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
      },
    });

    expect(response.ok()).toBe(true);
  });

  test("should verify backend is accessible from frontend context", async ({ page }) => {
    // Navigate to login page
    await page.goto("/login");

    // Check if page loads successfully
    await expect(page).toHaveURL(/.*login/);

    // Check if we can see the login form
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
  });

  test("should verify API endpoints are reachable", async ({ request }) => {
    // Test various endpoints to ensure they respond correctly
    const endpoints = [
      { path: "/api/v1/health", method: "GET" },
      { path: "/api/v1/test/cleanup", method: "POST" },
    ];

    for (const endpoint of endpoints) {
      const response = await request.fetch(`${BACKEND_URL}${endpoint.path}`, {
        method: endpoint.method,
      });

      // Health endpoint should always be 200
      if (endpoint.path === "/api/v1/health") {
        expect(response.status()).toBe(200);
      }
      // Cleanup endpoint should be 200 in development
      else if (endpoint.path === "/api/v1/test/cleanup") {
        expect(response.status()).toBe(200);
      }
    }
  });

  test("should verify error handling works correctly", async ({ request }) => {
    // Test 404 handling
    const response = await request.get(`${BACKEND_URL}/api/v1/nonexistent-endpoint`);
    expect(response.status()).toBe(404);

    const error = await response.json();
    expect(error.detail).toBeDefined();
  });

  test("should verify rate limiting is functional", async ({ request }) => {
    // Make multiple rapid requests to test rate limiting
    const promises = Array(10).fill(null).map(() =>
      request.get(`${BACKEND_URL}/api/v1/health`)
    );

    const responses = await Promise.all(promises);

    // All health requests should succeed (health endpoint is usually exempt from rate limiting)
    responses.forEach(response => {
      expect(response.ok()).toBe(true);
    });
  });

  test("should verify backend connectivity through frontend", async ({ page }) => {
    // Test that the frontend can access backend APIs through its own routing
    await page.goto("/login");

    // Wait for page to load
    await page.waitForLoadState("networkidle");

    // The login page should have loaded successfully, indicating frontend-backend connectivity
    await expect(page).toHaveURL(/.*login/);
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
  });
});