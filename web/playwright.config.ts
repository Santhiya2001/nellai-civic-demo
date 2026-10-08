import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  timeout: 60000,
  reporter: [['list'], ['html', { open: 'never', outputFolder: '../runtime/browser-report' }]],
  use: {
    baseURL: process.env.NELLAI_DEMO_URL || 'http://localhost:8080',
    viewport: { width: 1440, height: 1050 },
    browserName: 'chromium',
    launchOptions: { executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', args: ['--no-sandbox'] },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
});
