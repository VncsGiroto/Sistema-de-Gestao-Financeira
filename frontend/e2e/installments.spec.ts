import { expect, test } from "@playwright/test";

test("installments: criar + ver schedule somando o total", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `par_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Par");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/installments");
  await page.getByPlaceholder("Descrição").fill("Notebook E2E");
  await page.getByPlaceholder("Valor total").fill("1000");
  await page.getByPlaceholder("Nº parcelas").fill("3");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/notebook e2e/i)).toBeVisible({ timeout: 15000 });

  await page.getByRole("button", { name: /ver parcelas/i }).click();
  const rows = page.locator("tbody tr");
  await expect(rows).toHaveCount(3, { timeout: 15000 });
  const amounts = await rows.locator("td:nth-child(3)").allTextContents();
  const sum = amounts.reduce((a, t) => a + Number(t.replace(/[^\d,.-]/g, "").replace(",", ".")), 0);
  expect(sum).toBeCloseTo(1000, 2);
});
