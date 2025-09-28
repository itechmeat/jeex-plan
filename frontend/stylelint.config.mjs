export default {
  extends: ['stylelint-config-standard'],
  rules: {
    // Disable naming pattern rules to avoid conflicts
    'selector-class-pattern': null,
    'selector-id-pattern': null,
    'keyframes-name-pattern': null,

    // Allow modern CSS features
    'color-function-notation': null,
    'alpha-value-notation': null,
    'property-no-vendor-prefix': null,

    // Allow duplicate selectors (common in modular CSS)
    'no-duplicate-selectors': null,

    // Allow value keyword case variations
    'value-keyword-case': null,
  },
  ignoreFiles: ['**/dist/**', '**/node_modules/**', '**/.turbo/**'],
};
