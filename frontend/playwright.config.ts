import path from "node:path";

import { defineConfig } from "@playwright/test";

// Browser tests for the critical flows (BUILD-134). They run against their own
// backend (fresh SQLite DB, port 8020) and their own production build of the
// frontend (in .next-e2e, port 3020), so they never touch dev data or the
// .next folder of a running `next dev`.
//
//   npx playwright test            # build + run
//   npx playwright test --ui       # watch them run
const CI = !!process.env.CI;
// Absolute, forward-slash and quoted: the repo path may contain spaces, and backslashes get eaten by the shell.
const backend = path.resolve(__dirname, "../backend").split(path.sep).join("/");
const python =
  process.env.E2E_PYTHON ??
  (process.platform === "win32" ? `"${backend}/.venv/Scripts/python.exe"` : `"${backend}/.venv/bin/python"`);
const API = "http://127.0.0.1:8020/api/v1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: CI ? 1 : 0,
  reporter: CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3020",
    // Locally use the installed Chrome (no browser download); CI installs Chromium.
    channel: CI ? undefined : "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `${python} "${backend}/scripts/e2e_server.py" 8020`,
      url: `${API}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "npx next build && npx next start -p 3020",
      url: "http://localhost:3020/login",
      env: { NEXT_DIST_DIR: ".next-e2e", NEXT_PUBLIC_API_URL: API, NEXT_TELEMETRY_DISABLED: "1" },
      reuseExistingServer: false,
      timeout: 600_000,
    },
  ],
});
