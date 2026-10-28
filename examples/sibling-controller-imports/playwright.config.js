import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:8967', headless: true },
  webServer: {
    command: `${process.env.PHP_BINARY || 'php'} -S 127.0.0.1:8967 -t public public/router.php`,
    url: 'http://127.0.0.1:8967',
    reuseExistingServer: false,
    env: { APP_ENV: process.env.APP_ENV || 'dev' },
  },
});
