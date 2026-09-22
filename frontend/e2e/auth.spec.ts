import { expect, test } from "@playwright/test";

test("register → dashboard → logout → login", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `e2e_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("E2E");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.getByRole("button", { name: /sair/i }).click();
  await expect(page).toHaveURL(/login/);

  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder("Senha").fill("segredo-123");
  await page.getByRole("button", { name: /^entrar$/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });
});
