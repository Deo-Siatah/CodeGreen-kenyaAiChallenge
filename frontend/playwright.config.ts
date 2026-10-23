import { defineConfig, devices } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const configDir = path.dirname(fileURLToPath(import.meta.url));

function readEnv(filePath: string): Record<string, string> {
  const values: Record<string, string> = {};
  for (const line of readFileSync(filePath, 'utf8').split(/\r?\n/)) {
    if (!line || line.trimStart().startsWith('#') || !line.includes('=')) {
      continue;
    }
    const index = line.indexOf('=');
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim().replace(/^['"]|['"]$/g, '');
    values[key] = value;
  }
  return values;
}

function testDatabaseUrl(): string {
  const backendDir = path.resolve(configDir, '../backend');
  const env = readEnv(path.join(backendDir, '.env'));
  const testUrl = env.TEST_DATABASE_URL_DIRECT;
  const mainUrl = env.DATABASE_URL_DIRECT;

  if (!testUrl || !mainUrl) {
    throw new Error(
      'E2E needs TEST_DATABASE_URL_DIRECT and DATABASE_URL_DIRECT in backend/.env',
    );
  }

  const test = new URL(testUrl);
  const main = new URL(mainUrl);
  if (test.hostname === main.hostname) {
    throw new Error('Refusing e2e: TEST_DATABASE_URL_DIRECT points at main');
  }
  if (test.hostname.includes('-pooler')) {
    throw new Error(
      'Refusing e2e: TEST_DATABASE_URL_DIRECT must use the direct endpoint',
    );
  }

  return testUrl;
}

const processEnv = Object.fromEntries(
  Object.entries(process.env).filter(
    (entry): entry is [string, string] => typeof entry[1] === 'string',
  ),
);

const apiUrl = 'http://127.0.0.1:8001';
const frontendUrl = 'http://localhost:5174';
const databaseUrl = testDatabaseUrl();
const backendDir = path.resolve(configDir, '../backend');

export default defineConfig({
  testDir: './src/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  timeout: 180_000,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: frontendUrl,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
    },
    {
      name: 'Google Chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    },
  ],
  webServer: [
    {
      command:
        '.\\.venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001 --timeout-graceful-shutdown 1 --timeout-keep-alive 5',
      cwd: backendDir,
      url: `${apiUrl}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...processEnv,
        DATABASE_URL_POOLED: databaseUrl,
        DATABASE_URL_DIRECT: databaseUrl,
        FARM_ACTIVITY_PROVIDER: 'null',
        ALLOWED_ORIGINS: JSON.stringify([
          'http://localhost:5173',
          'http://localhost:5174',
        ]),
      },
    },
    {
      command: 'npm run dev -- --port 5174 --strictPort',
      url: frontendUrl,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...processEnv,
        VITE_API_URL: apiUrl,
      },
    },
  ],
});
