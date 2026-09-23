import { expect, test } from "@playwright/test";

test("bills: criar recorrente + única + filtro próximas", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `bil_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Bil");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/bills");
  await page.getByPlaceholder("Descrição").fill("Internet E2E");
  await page.getByPlaceholder("Valor").fill("120");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/internet e2e/i)).toBeVisible({ timeout: 15000 });

  // conta única com data
  await page.getByPlaceholder("Descrição").fill("Única E2E");
  await page.getByPlaceholder("Valor").fill("50");
  await page.locator("form select").first().selectOption("ONE_TIME");
  await page.locator('form input[type="date"]').fill("2099-01-05");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/única e2e/i)).toBeVisible({ timeout: 15000 });

  // filtro próximas 30d: esconde a de 2099
  await page.getByText(/próximas 30d/i).click();
  await expect(page.getByText(/única e2e/i)).toBeHidden({ timeout: 15000 });
  await expect(page.getByText(/internet e2e/i)).toBeVisible({ timeout: 15000 });
});
