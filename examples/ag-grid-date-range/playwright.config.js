import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    channel: 'chromium',
    baseURL: 'http://127.0.0.1:4189',
  },
  webServer: {
    command: 'vite preview --host 127.0.0.1 --port 4189 --strictPort',
    url: 'http://127.0.0.1:4189',
  },
});
