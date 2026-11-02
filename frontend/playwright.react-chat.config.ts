import { defineConfig } from '@playwright/test'
import path from 'node:path'
export default defineConfig({ testDir: './e2e-react-chat', timeout: 90_000, workers: 1, retries: 0, reporter: [['list']], outputDir: path.resolve(import.meta.dirname, 'test-results/react-chat'), use: { actionTimeout: 15_000, baseURL: `http://localhost:${process.env.CHAT_HOST_PORT || 5188}`, headless: true, viewport: { width: 1360, height: 1100 }, trace: 'off', screenshot: 'only-on-failure', launchOptions: process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {} } })
