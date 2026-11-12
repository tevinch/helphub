import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  reporter: 'list',
  use: {
    channel: process.env.PLAYWRIGHT_CHANNEL,
    headless: true,
    baseURL: 'http://127.0.0.1:4179',
  },
  webServer: {
    command: 'npm run dev -- --port 4179 --strictPort',
    url: 'http://127.0.0.1:4179',
    reuseExistingServer: false,
  },
});
