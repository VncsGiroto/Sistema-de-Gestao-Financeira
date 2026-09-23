import { expect, test } from "@playwright/test";

test("recover responde sem vazar existência + change troca a senha", async ({ page }) => {
  await page.goto("/recover");
  await page.getByPlaceholder("E-mail").fill(`inexistente_${Date.now()}@exemplo.com`);
  await page.getByRole("button", { name: /enviar/i }).click();
  await expect(page.getByText(/se o e-mail existir/i)).toBeVisible({ timeout: 15000 });

  const uniq = Date.now().toString(36);
  const email = `sec_${uniq}@exemplo.com`;
  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Sec");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/security");
  await page.getByPlaceholder("Senha atual").fill("segredo-123");
  await page.getByPlaceholder(/Nova senha/).fill("nova-senha-2");
  await page.locator("form").getByRole("button", { name: /trocar senha/i }).click();
  await expect(page).toHaveURL(/login/, { timeout: 15000 });

  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder("Senha").fill("nova-senha-2");
  await page.getByRole("button", { name: /^entrar$/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });
});
