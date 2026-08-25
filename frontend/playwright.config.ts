import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end test config for the OSCE web app.
 *
 * - Backend (Flask) is served on 127.0.0.1:5000.
 * - Frontend (Nuxt) is served on 127.0.0.1:3000.
 * - We use the full Chromium build (`channel: 'chromium'`) because the
 *   separate chromium-headless-shell binary is not installed in this env;
 *   the full build renders pages in headless fine.
 *
 * Servers are started automatically via `webServer` (reused if already up).
 * Run with:  cd frontend && pnpm e2e
 */
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:5000'
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:3000'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: FRONTEND_URL,
    channel: 'chromium',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command:
        "cd ../backend && LLM_MOCK=1 ./.venv/bin/python -c \"from app import app; app.run(host='127.0.0.1', port=5000)\"",
      url: `${BACKEND_URL}/api/health`,
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      // Use the nuxt binary directly (not `pnpm dev`) so the runner never
      // touches the pnpm store, which is read-only in the harness sandbox.
      command: './node_modules/.bin/nuxt dev --port 3000',
      url: FRONTEND_URL,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
})
