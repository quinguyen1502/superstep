import path from 'node:path'
import { defineConfig } from '@playwright/test'
import host from './playwright.chat-host.config'
export default defineConfig({ ...host, testDir: './e2e-widget-chat', outputDir: path.resolve(import.meta.dirname, 'test-results/widget-chat') })
