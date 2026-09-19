import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './specs',
  workers: 1,
  fullyParallel: false,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: { baseURL: process.env.BASE_URL || 'http://localhost:8000', trace: 'retain-on-failure' },
});
