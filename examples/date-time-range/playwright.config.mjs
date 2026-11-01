import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: 'browser.spec.mjs', fullyParallel: false,
  use: { baseURL: 'http://127.0.0.1:4176', timezoneId: 'UTC' },
  webServer: { command: 'node server.mjs', url: 'http://127.0.0.1:4176', reuseExistingServer: false },
  projects: [{ name: 'desktop', use: { viewport: { width: 1280, height: 1000 } } },
    { name: 'mobile', use: { viewport: { width: 375, height: 900 } } }],
});
