import { expect, test } from "@playwright/test";

import { registerViaApi, signIn, unique } from "./helpers";

test("sign up creates a company and lands on the dashboard", async ({ page }) => {
  const id = unique();
  await page.goto("/register");
  await page.getByLabel("Company name").fill(`Harbour Builders ${id}`);
  await page.getByLabel("Company code").fill(`HB-${id}`);
  await page.getByLabel("Your full name").fill("Amina Khan");
  await page.getByLabel("Email").fill(`amina-${id}@example.com`);
  await page.getByLabel("Password").fill("a-good-password");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: /Good (morning|afternoon|evening), Amina/ })).toBeVisible();
});

test("wrong password is refused, right one signs in, and log out returns to login", async ({ page, request }) => {
  const account = await registerViaApi(request);
  await page.goto("/login");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Invalid email or password")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);

  await signIn(page, account.email.toUpperCase(), account.password); // email case doesn't matter
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  // Signed out means signed out: protected pages bounce back to login.
  await page.goto("/projects");
  await expect(page).toHaveURL(/\/login$/);
});
