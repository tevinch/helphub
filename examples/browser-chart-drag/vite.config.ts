import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';
import type {} from '@vitest/browser/providers/playwright';

export default defineConfig({
  plugins: [react()],
  test: {
    include: ['test/**/*.test.tsx'],
    testTimeout: 15_000,
    browser: {
      enabled: true,
      provider: 'playwright',
      headless: true,
      screenshotFailures: false,
      viewport: { width: 1000, height: 700 },
      instances: [{
        browser: 'chromium',
        launch: process.env.CHROME_CHANNEL ? { channel: process.env.CHROME_CHANNEL } : {},
      }],
      commands: {
        async moveToLabel({ page, iframe }, label: string) {
          const tick = iframe
            .locator('.recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value')
            .filter({ hasText: new RegExp(`^${label}$`) });
          const tickBox = await tick.boundingBox();
          const chartBox = await iframe.locator('.recharts-surface').boundingBox();
          if (!tickBox || !chartBox) throw new Error('The chart must have native browser geometry.');
          await page.mouse.move(tickBox.x + tickBox.width / 2, chartBox.y + chartBox.height / 2);
        },
        async moveOutside({ page }) {
          await page.mouse.move(0, 0);
        },
        async press({ page }) {
          await page.mouse.down({ button: 'left' });
        },
        async release({ page }) {
          await page.mouse.up({ button: 'left' });
        },
      },
    },
  },
});
