import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The Flask API runs on :5000 in development; everything under /api is proxied to it.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:5000', changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
});
