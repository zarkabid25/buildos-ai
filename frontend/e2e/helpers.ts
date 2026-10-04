import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const API = "http://127.0.0.1:8020/api/v1";

let counter = 0;
/** A unique suffix so every test gets its own company and emails. */
export function unique(): string {
  counter += 1;
  return `${Date.now().toString(36)}${counter}`;
}

export interface Account {
  email: string;
  password: string;
  token: string;
  companyName: string;
}

/** Register a company + admin straight through the API (fast setup for tests that aren't about sign-up). */
export async function registerViaApi(request: APIRequestContext, name = "Test Admin"): Promise<Account> {
  const id = unique();
  const account = { email: `admin-${id}@example.com`, password: "a-good-password", companyName: `Co ${id}` };
  const res = await request.post(`${API}/auth/register`, {
    data: { company_name: account.companyName, company_code: `C-${id}`, full_name: name, ...account },
  });
  expect(res.status(), await res.text()).toBe(201);
  return { ...account, token: (await res.json()).access_token };
}

/** Make API calls as a user, failing loudly on any non-2xx. */
export function apiAs(request: APIRequestContext, token: string) {
  const headers = { Authorization: `Bearer ${token}` };
  return {
    async post<T = any>(path: string, data: unknown = {}): Promise<T> {
      const res = await request.post(`${API}${path}`, { data, headers });
      expect(res.ok(), `${path}: ${await res.text()}`).toBeTruthy();
      return (await res.json()) as T;
    },
  };
}

/** Sign in through the real login page. */
export async function signIn(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}
