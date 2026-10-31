import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite-plus'

// API base for the dev server proxy; the production build is served by FastAPI on the same origin.
const apiTarget = process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: { '/api': apiTarget },
  },
  fmt: {
    // coss ui components are vendored via the shadcn CLI; keep them byte-identical to the registry
    ignorePatterns: ['dist/**', 'src/components/ui/**', 'src/hooks/use-media-query.ts', 'components.json'],
    singleQuote: true,
    semi: false,
    printWidth: 120,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    passWithNoTests: true,
  },
})
