import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: { conditions: ['source', 'module', 'browser', 'development|production'], alias: { '@': path.resolve(__dirname, './src') } },
  esbuild: { jsx: 'automatic' },  // component tests (.test.tsx) use the same JSX runtime as the app
  test: { environment: 'jsdom', include: ['src/**/*.test.ts', 'src/**/*.test.tsx'] },
})
