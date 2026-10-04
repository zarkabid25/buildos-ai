import { expect, test } from "@playwright/test";

import { apiAs, registerViaApi, signIn } from "./helpers";

test("RFQ → compare quotes → award → approve PO → pay, with overpayment refused", async ({ page, request }) => {
  const admin = await registerViaApi(request);
  const api = apiAs(request, admin.token);

  // Setup through the API: this test is about the procurement screens, not data entry.
  const project = await api.post("/projects", { name: "Harbour Tower", code: "HT-1", budget: "5000000" });
  const acme = await api.post("/suppliers", { name: "Acme Cement" });
  const beta = await api.post("/suppliers", { name: "Beta Steel" });
  const cement = await api.post("/materials", { name: "Cement", sku: "CEM", unit: "Bag" });
  const steel = await api.post("/materials", { name: "Steel rebar", sku: "STL", unit: "Ton" });
  const rfq = await api.post("/rfqs", {
    title: "Level 3 slab",
    project_id: project.id,
    items: [
      { material_id: cement.id, quantity: "500" },
      { material_id: steel.id, quantity: "4" },
    ],
    supplier_ids: [acme.id, beta.id],
  });
  const itemId = (name: string) => rfq.items.find((i: { material_name: string }) => i.material_name === name).id;
  for (const [supplier, cementRate, steelRate] of [
    [acme, "1400", "285000"], // 700,000 + 1,140,000 = 1,840,000
    [beta, "1450", "270000"], // 725,000 + 1,080,000 = 1,805,000 (lowest)
  ]) {
    await api.post(`/rfqs/${rfq.id}/quotations`, {
      supplier_id: supplier.id,
      items: [
        { rfq_item_id: itemId("Cement"), rate: cementRate },
        { rfq_item_id: itemId("Steel rebar"), rate: steelRate },
      ],
    });
  }

  await signIn(page, admin.email, admin.password);

  // Compare: exact totals, lowest flagged.
  await page.goto("/rfqs");
  await page.getByRole("button", { name: "RFQ-1001" }).click();
  await expect(page.getByRole("cell", { name: /PKR 1,805,000\s*lowest/ })).toBeVisible();
  await expect(page.getByRole("cell", { name: "PKR 1,840,000" })).toBeVisible();

  // Award the cheapest (quotes are listed cheapest first) after confirming.
  await page.getByRole("button", { name: "Award", exact: true }).first().click();
  const award = page.getByRole("alertdialog");
  await expect(award).toContainText("Award to Beta Steel?");
  await expect(award).toContainText("PKR 1,805,000");
  await award.getByRole("button", { name: "Award and draft PO" }).click();
  await expect(page.getByText(/Awarded\. PO-1001 was drafted/)).toBeVisible();

  // The drafted PO still needs approval.
  await page.goto("/procurement");
  const poRow = page.getByRole("row", { name: /PO-1001/ });
  await expect(poRow).toContainText("pending approval");
  await poRow.getByRole("button", { name: "Approve" }).click();
  const approve = page.getByRole("alertdialog");
  await expect(approve).toContainText("commits PKR 1,805,000");
  await approve.getByRole("button", { name: "Approve" }).click();
  await expect(poRow).toContainText("approved");
  await expect(poRow).toContainText("Unpaid");

  // Pay part of it.
  await page.goto("/payments");
  await page.getByLabel("Purchase order").selectOption({ label: "PO-1001 · Beta Steel · owed PKR 1,805,000" });
  await expect(page.locator("#paid_on_amount")).toHaveValue("1805000.00"); // pre-filled with what's owed
  await page.locator("#paid_on_amount").fill("1000000");
  await page.locator("#paid_on_method").selectOption("cheque");
  await page.locator("#paid_on_ref").fill("CHQ-0042");
  await page.getByRole("button", { name: "Record payment" }).click();
  await expect(page.getByRole("row", { name: /Beta Steel\s+PKR 1,805,000\s+PKR 1,000,000\s+PKR 805,000/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /CHQ-0042/ })).toContainText("−PKR 1,000,000");

  // Trying to pay more than is owed: warned in the form and refused by the server.
  await page.getByLabel("Purchase order").selectOption({ label: "PO-1001 · Beta Steel · owed PKR 805,000" });
  await page.locator("#paid_on_amount").fill("900000");
  await expect(page.getByText("That's more than the PKR 805,000 outstanding on PO-1001.")).toBeVisible();
  await page.getByRole("button", { name: "Record payment" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "That would overpay PO-1001" })).toBeVisible();
});
