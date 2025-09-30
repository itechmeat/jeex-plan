import react from '@vitejs/plugin-react';
import postcssNesting from 'postcss-nesting';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5200,
    host: true,
  },
  css: {
    modules: {
      localsConvention: 'camelCaseOnly',
    },
    postcss: {
      plugins: [postcssNesting],
    },
  },
});
