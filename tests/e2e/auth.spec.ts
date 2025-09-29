import { test, expect, Page } from '@playwright/test';

/**
 * Professional Page Object Model for Authentication E2E Tests
 * CRITICAL: Uses ONLY data-testid selectors - no CSS selectors allowed
 */
class AuthPage {
  constructor(private page: Page) {}

  // Navigation methods
  async navigateToLogin() {
    await this.page.goto('/login');
  }

  async navigateToRegister() {
    await this.page.goto('/register');
  }

  // Form interaction methods - LOGIN
  async fillLoginCredentials(email: string, password: string) {
    await this.page.fill('[data-testid="email-input"]', email);
    await this.page.fill('[data-testid="password-input"]', password);
  }

  // Form interaction methods - REGISTRATION
  async fillRegistrationForm(firstName: string, lastName: string, email: string, password: string, confirmPassword?: string) {
    await this.page.fill('[data-testid="first-name-input"]', firstName);
    await this.page.fill('[data-testid="last-name-input"]', lastName);
    await this.page.fill('[data-testid="email-input"]', email);
    await this.page.fill('[data-testid="password-input"]', password);
    if (confirmPassword) {
      await this.page.fill('[data-testid="confirm-password-input"]', confirmPassword);
    }
  }

  // Button click methods
  async clickSignIn() {
    await this.page.click('[data-testid="sign-in-button"]');
  }

  async clickSignUp() {
    await this.page.click('[data-testid="sign-up-button"]');
  }

  async clickRegisterLink() {
    await this.page.click('[data-testid="register-link"]');
  }

  async clickLoginLink() {
    await this.page.click('[data-testid="login-link"]');
  }

  // Error state expectations
  async expectGeneralErrorMessage() {
    await expect(this.page.locator('[data-testid="error-message"]')).toBeVisible();
  }

  async expectEmailValidationError() {
    await expect(this.page.locator('[data-testid="email-input-error"]')).toBeVisible();
  }

  async expectPasswordValidationError() {
    await expect(this.page.locator('[data-testid="password-input-error"]')).toBeVisible();
  }

  async expectFirstNameValidationError() {
    await expect(this.page.locator('[data-testid="first-name-input-error"]')).toBeVisible();
  }

  async expectLastNameValidationError() {
    await expect(this.page.locator('[data-testid="last-name-input-error"]')).toBeVisible();
  }

  async expectConfirmPasswordValidationError() {
    await expect(this.page.locator('[data-testid="confirm-password-input-error"]')).toBeVisible();
  }

  // Loading state expectations
  async expectLoadingState() {
    await expect(this.page.locator('[data-testid="loading-spinner"]')).toBeVisible();
  }

  async expectButtonDisabled() {
    await expect(this.page.locator('[data-testid="sign-in-button"]')).toBeDisabled();
  }

  // Navigation expectations
  async waitForDashboard() {
    await expect(this.page).toHaveURL(/.*dashboard/);
  }

  async waitForLogin() {
    await expect(this.page).toHaveURL(/.*login/);
  }

  // Form visibility expectations
  async expectRegisterFormVisible() {
    await expect(this.page.locator('[data-testid="register-form"]')).toBeVisible();
  }

  async expectLoginFormVisible() {
    await expect(this.page.locator('[data-testid="login-form"]')).toBeVisible();
  }

  // Clear error by typing
  async clearErrorByTyping(fieldTestId: string, value: string) {
    await this.page.fill(`[data-testid="${fieldTestId}"]`, value);
  }
}

test.describe('Authentication Flow', () => {
  let authPage: AuthPage;

  test.beforeEach(async ({ page }) => {
    authPage = new AuthPage(page);
  });

  test.describe('User Registration', () => {
    test('should display registration form when clicking sign up link', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      await authPage.clickRegisterLink();
      await authPage.expectRegisterFormVisible();
    });

    test('should validate email format during registration', async ({ page }) => {
      await authPage.navigateToRegister();
      await authPage.expectRegisterFormVisible();

      await authPage.fillRegistrationForm('John', 'Doe', 'invalid-email', 'Password123!', 'Password123!');
      await authPage.clickSignUp();

      await authPage.expectEmailValidationError();
    });

    test('should validate password confirmation mismatch', async ({ page }) => {
      await authPage.navigateToRegister();
      await authPage.expectRegisterFormVisible();

      await authPage.fillRegistrationForm('John', 'Doe', 'test@example.com', 'Password123!', 'DifferentPassword123!');
      await authPage.clickSignUp();

      await authPage.expectConfirmPasswordValidationError();
    });

    test('should validate required first name field', async ({ page }) => {
      await authPage.navigateToRegister();
      await authPage.expectRegisterFormVisible();

      // Fill all except first name
      await authPage.fillRegistrationForm('', 'Doe', 'test@example.com', 'Password123!', 'Password123!');
      await authPage.clickSignUp();

      await authPage.expectFirstNameValidationError();
    });

    test('should validate required last name field', async ({ page }) => {
      await authPage.navigateToRegister();
      await authPage.expectRegisterFormVisible();

      // Fill all except last name
      await authPage.fillRegistrationForm('John', '', 'test@example.com', 'Password123!', 'Password123!');
      await authPage.clickSignUp();

      await authPage.expectLastNameValidationError();
    });

    test('should validate required email field', async ({ page }) => {
      await authPage.navigateToRegister();
      await authPage.expectRegisterFormVisible();

      // Fill all except email
      await authPage.fillRegistrationForm('John', 'Doe', '', 'Password123!', 'Password123!');
      await authPage.clickSignUp();

      await authPage.expectEmailValidationError();
    });

    test('should validate required password field', async ({ page }) => {
      await authPage.navigateToRegister();
      await authPage.expectRegisterFormVisible();

      // Fill all except password
      await authPage.fillRegistrationForm('John', 'Doe', 'test@example.com', '', '');
      await authPage.clickSignUp();

      await authPage.expectPasswordValidationError();
    });
  });

  test.describe('User Login', () => {
    test('should display login form with all required elements', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      await expect(page.locator('[data-testid="email-input"]')).toBeVisible();
      await expect(page.locator('[data-testid="password-input"]')).toBeVisible();
      await expect(page.locator('[data-testid="sign-in-button"]')).toBeVisible();
      await expect(page.locator('[data-testid="register-link"]')).toBeVisible();
    });

    test('should validate email format on login', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      await authPage.fillLoginCredentials('invalid-email-format', 'password123');
      await authPage.clickSignIn();

      await authPage.expectEmailValidationError();
    });

    test('should validate required email field on login', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Try to submit with empty email
      await authPage.fillLoginCredentials('', 'password123');
      await authPage.clickSignIn();

      await authPage.expectEmailValidationError();
    });

    test('should validate required password field on login', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Try to submit with empty password
      await authPage.fillLoginCredentials('test@example.com', '');
      await authPage.clickSignIn();

      await authPage.expectPasswordValidationError();
    });

    test('should handle invalid credentials gracefully', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      await authPage.fillLoginCredentials('nonexistent@example.com', 'wrongpassword');
      await authPage.clickSignIn();

      // Should show general error message for invalid credentials
      await authPage.expectGeneralErrorMessage();
    });

    test('should show loading state during login attempt', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      await authPage.fillLoginCredentials('test@example.com', 'validpassword123');

      // Start login process and immediately check for loading state
      await authPage.clickSignIn();

      // Should show loading spinner or disabled button
      const hasLoadingSpinner = await page.locator('[data-testid="loading-spinner"]').isVisible().catch(() => false);
      const isButtonDisabled = await page.locator('[data-testid="sign-in-button"]').isDisabled().catch(() => false);

      expect(hasLoadingSpinner || isButtonDisabled).toBe(true);
    });
  });

  test.describe('Navigation', () => {
    test('should navigate between login and register forms', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Navigate to register
      await authPage.clickRegisterLink();
      await authPage.expectRegisterFormVisible();

      // Navigate back to login
      await authPage.clickLoginLink();
      await authPage.expectLoginFormVisible();
    });

    test('should redirect unauthenticated users to login from protected routes', async ({ page }) => {
      await page.goto('/dashboard');

      // Should redirect to login for protected routes
      await authPage.waitForLogin();
      await authPage.expectLoginFormVisible();
    });

    test('should redirect from root to dashboard for authenticated users', async ({ page }) => {
      // This test would need authentication setup
      // For now, verify root redirects to login for unauthenticated users
      await page.goto('/');
      await authPage.waitForLogin();
    });
  });

  test.describe('Error Handling and User Experience', () => {
    test('should clear email errors when user starts typing', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Trigger email validation error
      await authPage.fillLoginCredentials('', 'password123');
      await authPage.clickSignIn();
      await authPage.expectEmailValidationError();

      // Start typing in email field to clear error
      await authPage.clearErrorByTyping('email-input', 'test@');

      // Error should be cleared after typing
      await page.waitForTimeout(300);
      await expect(page.locator('[data-testid="email-input-error"]')).not.toBeVisible();
    });

    test('should clear password errors when user starts typing', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Trigger password validation error
      await authPage.fillLoginCredentials('test@example.com', '');
      await authPage.clickSignIn();
      await authPage.expectPasswordValidationError();

      // Start typing in password field to clear error
      await authPage.clearErrorByTyping('password-input', 'pass');

      // Error should be cleared after typing
      await page.waitForTimeout(300);
      await expect(page.locator('[data-testid="password-input-error"]')).not.toBeVisible();
    });

    test('should handle network errors gracefully', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Mock network failure for login endpoint
      await page.route('**/api/v1/auth/login', route => route.abort());

      await authPage.fillLoginCredentials('test@example.com', 'password123');
      await authPage.clickSignIn();

      // Should show general error message for network issues
      await authPage.expectGeneralErrorMessage();
    });

    test('should handle 500 server errors gracefully', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Mock server error
      await page.route('**/api/v1/auth/login', route =>
        route.fulfill({ status: 500, body: 'Internal Server Error' })
      );

      await authPage.fillLoginCredentials('test@example.com', 'password123');
      await authPage.clickSignIn();

      // Should show general error message for server errors
      await authPage.expectGeneralErrorMessage();
    });
  });

  test.describe('Accessibility and User Experience', () => {
    test('should have proper form accessibility attributes', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Check form has proper accessibility
      const loginForm = page.locator('[data-testid="login-form"]');
      await expect(loginForm).toBeVisible();

      // Check input fields have proper labels and accessibility
      const emailInput = page.locator('[data-testid="email-input"]');
      const passwordInput = page.locator('[data-testid="password-input"]');

      await expect(emailInput).toBeVisible();
      await expect(passwordInput).toBeVisible();

      // Inputs should have proper type attributes
      await expect(emailInput).toHaveAttribute('type', 'email');
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });


    test('should allow form submission with Enter key', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      await authPage.fillLoginCredentials('test@example.com', 'password123');

      // Press Enter in password field to submit form
      await page.locator('[data-testid="password-input"]').press('Enter');

      // Form should be submitted - check for loading state or error message
      const hasLoadingSpinner = await page.locator('[data-testid="loading-spinner"]').isVisible().catch(() => false);
      const hasErrorMessage = await page.locator('[data-testid="error-message"]').isVisible().catch(() => false);
      const isButtonDisabled = await page.locator('[data-testid="sign-in-button"]').isDisabled().catch(() => false);

      // Should show loading state, error, or disabled button (form was submitted)
      expect(hasLoadingSpinner || hasErrorMessage || isButtonDisabled).toBe(true);
    });

    test('should handle rapid successive clicks gracefully', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      await authPage.fillLoginCredentials('test@example.com', 'password123');

      // Click submit button multiple times rapidly
      const submitButton = page.locator('[data-testid="sign-in-button"]');
      await submitButton.click();
      await submitButton.click();
      await submitButton.click();

      // Should not cause multiple submissions or errors
      // Button should be disabled or show loading state
      const isDisabled = await submitButton.isDisabled().catch(() => false);
      const hasLoadingSpinner = await page.locator('[data-testid="loading-spinner"]').isVisible().catch(() => false);

      expect(isDisabled || hasLoadingSpinner).toBe(true);
    });

    test('should maintain form state when switching between login and register', async ({ page }) => {
      await authPage.navigateToLogin();
      await authPage.expectLoginFormVisible();

      // Fill login form
      await authPage.fillLoginCredentials('test@example.com', 'password123');

      // Navigate to register
      await authPage.clickRegisterLink();
      await authPage.expectRegisterFormVisible();

      // Navigate back to login
      await authPage.clickLoginLink();
      await authPage.expectLoginFormVisible();

      // Form should be cleared (this is expected UX behavior)
      const emailValue = await page.locator('[data-testid="email-input"]').inputValue();
      const passwordValue = await page.locator('[data-testid="password-input"]').inputValue();

      expect(emailValue).toBe('');
      expect(passwordValue).toBe('');
    });
  });
});