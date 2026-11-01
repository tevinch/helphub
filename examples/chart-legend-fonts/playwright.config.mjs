import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: 'browser.spec.mjs',
  use: { baseURL: 'http://127.0.0.1:4177' },
  webServer: { command: 'node server.mjs', url: 'http://127.0.0.1:4177', reuseExistingServer: false },
  projects: [{ name: 'desktop', use: { viewport: { width: 1280, height: 900 } } },
    { name: 'mobile', use: { viewport: { width: 375, height: 900 } } }],
});
