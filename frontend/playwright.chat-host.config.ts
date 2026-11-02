import { defineConfig } from '@playwright/test'
import path from 'node:path'

export default defineConfig({
  testDir: './e2e-chat-host',
  timeout: 90_000,
  workers: 1,
  retries: 0, // Revocation is terminal; each CI/script run seeds a fresh backend/key.
  reporter: [['list']],
  outputDir: path.resolve(import.meta.dirname, 'test-results/chat-host'),
  use: {
    baseURL: `http://localhost:${process.env.CHAT_HOST_PORT || 5188}`,
    headless: true,
    locale: 'en-US',
    viewport: { width: 1280, height: 1000 },
    trace: 'off', // Network traces contain short-lived auth frames; retain UI-only screenshots instead.
    screenshot: 'only-on-failure',
    launchOptions: process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {},
  },
})
