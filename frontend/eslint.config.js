import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default [
  {
    ignores: ['dist', 'node_modules'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      // Base rules
      ...reactHooks.configs.recommended.rules,
      ...reactRefresh.configs.vite.rules,

      // TypeScript specific rules aligned with CodeRabbit
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
      '@typescript-eslint/no-explicit-any': 'warn', // CodeRabbit handles this
      '@typescript-eslint/no-inferrable-types': 'off', // Allow explicit types for clarity

      // React/JSX rules
      'react-hooks/exhaustive-deps': 'warn', // CodeRabbit can provide context
      'react-refresh/only-export-components': [
        'warn',
        {
          allowConstantExport: true,
        },
      ],

      // Code quality rules (aligned with CodeRabbit focus areas)
      'no-console': 'off',
      'no-debugger': 'error',
      'no-duplicate-imports': 'error',
      'prefer-const': 'error',

      // Rules that CodeRabbit handles better - relaxed here
      'no-empty': 'warn', // CodeRabbit provides better context
      'no-unused-expressions': 'off', // Can conflict with React patterns
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  // Test files configuration
  {
    files: ['**/*.test.{ts,tsx}', '**/*.spec.{ts,tsx}'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off', // Allow any in tests
      'no-console': 'off', // Allow console in tests
    },
  },
];
