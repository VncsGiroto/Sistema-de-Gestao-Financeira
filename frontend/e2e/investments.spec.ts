import { expect, test } from "@playwright/test";

test("investments: ativo + aporte + preço manual + posição", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `inv_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Inv");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/investments");
  await page.getByPlaceholder("Ticker").fill(`TST${uniq.slice(0, 4).toUpperCase()}`);
  await page.locator("form").first().locator("select").first().selectOption("OUTROS");
  await page.getByPlaceholder("Subtipo").fill("OUTRO");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(new RegExp(`tst${uniq.slice(0, 4)}`, "i"))).toBeVisible({ timeout: 15000 });

  // detalha, aporta e precifica
  await page.getByRole("button", { name: /detalhar/i }).click();
  await page.getByPlaceholder("Quantidade").fill("10");
  await page.getByPlaceholder("Preço").first().fill("100");
  await page.getByRole("button", { name: /^lançar$/i }).click();
  await page.getByPlaceholder("Preço manual").fill("120");
  await page.getByRole("button", { name: /precificar/i }).click();
  await expect(page.getByText(/P&L/i)).toBeVisible({ timeout: 15000 });
  // /returns aguarda fail-open dos benchmarks (BCB público): latência fria pode
  // estourar 15s na primeira chamada; valores não importam, só a presença.
  await expect(page.getByText(/XIRR/i)).toBeVisible({ timeout: 60000 });
});
