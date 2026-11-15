import { defineConfig, loadEnv } from 'vite';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig(({mode})=>({
  root: 'frontend',
  base: process.env.FIREATLAS_BASE_PATH || '/',
  plugins: [tailwindcss()],
  build: { outDir: '../dist', emptyOutDir: true },
  server: { proxy: { '/api': process.env.FIREATLAS_API_URL || loadEnv(mode, process.cwd(), 'FIREATLAS_').FIREATLAS_API_URL || 'http://127.0.0.1:8000' } },
}));
