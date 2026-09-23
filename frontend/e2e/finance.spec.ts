import { expect, test } from "@playwright/test";

test("finance: conta + categoria + lançamento + categoria inline", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `fin_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Fin");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  // conta
  await page.goto("/app/accounts");
  await page.getByPlaceholder("Nome").fill("Corrente E2E");
  await page.getByPlaceholder("Banco").fill("Banco X");
  await page.getByPlaceholder("Saldo inicial").fill("100");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/corrente e2e/i)).toBeVisible({ timeout: 15000 });

  // categoria
  await page.goto("/app/categories");
  await page.getByPlaceholder("Nome").fill(`Mercado ${uniq}`);
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(new RegExp(`mercado ${uniq}`, "i"))).toBeVisible({ timeout: 15000 });

  // lançamento
  await page.goto("/app/transactions");
  await page.getByPlaceholder("Descrição").fill("SUPERMERCADO E2E");
  await page.getByPlaceholder("Valor").fill("-42.50");
  await page.locator("form").filter({ hasText: "Adicionar" }).locator("select").first().selectOption({ index: 1 });
  await page.getByRole("button", { name: /^adicionar$/i }).click();
  await expect(page.getByText(/supermercado e2e/i)).toBeVisible({ timeout: 15000 });

  // categoria inline: primeira linha, seleciona a categoria criada
  const catLabel = `Mercado ${uniq}`;
  const row = page.locator("tbody tr", { hasText: "SUPERMERCADO E2E" }).first();
  await row.locator("select").selectOption({ label: catLabel });
  await expect(row.locator("select option:checked")).toHaveText(catLabel, { timeout: 15000 });
});
