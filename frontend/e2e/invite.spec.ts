import { expect, test } from "@playwright/test";

import { registerViaApi, signIn, unique } from "./helpers";

test("an admin invites someone, who joins with the given role", async ({ page, browser, request }) => {
  const admin = await registerViaApi(request, "Owner Person");
  const inviteeEmail = `site-${unique()}@example.com`;

  await signIn(page, admin.email, admin.password);
  await page.goto("/settings");
  await page.getByLabel("Invitee email").fill(inviteeEmail);
  await page.getByLabel("Invitee name (optional)").fill("Bilal Site");
  await page.getByLabel("Invitee role").selectOption("site_engineer");
  await page.getByRole("button", { name: "Create invite link" }).click();
  const link = await page.getByLabel("Invite link").inputValue();
  expect(link).toContain("/accept-invite?token=");
  await expect(page.getByText(inviteeEmail).last()).toBeVisible(); // listed as pending

  // The invitee opens the link in their own browser session.
  const invitee = await (await browser.newContext()).newPage();
  await invitee.goto(link);
  await expect(invitee.getByText(admin.companyName)).toBeVisible();
  await expect(invitee.getByText("Site engineer")).toBeVisible();
  await expect(invitee.getByLabel("Your name")).toHaveValue("Bilal Site");
  await invitee.getByLabel("Choose a password").fill("short");
  await invitee.getByLabel("Repeat password").fill("short");
  await invitee.getByRole("button", { name: "Join and sign in" }).click();
  await expect(invitee.getByText("At least 8 characters")).toBeVisible();

  await invitee.getByLabel("Choose a password").fill("site-password-1");
  await invitee.getByLabel("Repeat password").fill("site-password-1");
  await invitee.getByRole("button", { name: "Join and sign in" }).click();
  await expect(invitee).toHaveURL(/\/dashboard$/);
  await expect(invitee.getByText("Bilal Site")).toBeVisible();

  // The link is single-use.
  await invitee.goto(link);
  await expect(invitee.getByText(/isn't valid/)).toBeVisible();

  // The admin now sees them in the team.
  await page.reload();
  await expect(page.getByRole("cell", { name: inviteeEmail })).toBeVisible();
});
