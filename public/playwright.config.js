const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://localhost:8000',
    headless: true,
  },
});
