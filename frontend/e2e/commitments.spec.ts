import { expect, test } from "@playwright/test";

test("agenda: conta futura + parcela aparecem nos compromissos", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `com_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Com");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/bills");
  await page.getByPlaceholder("Descrição").fill("Internet Agenda");
  await page.getByPlaceholder("Valor").fill("120");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/internet agenda/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/installments");
  await page.getByPlaceholder("Descrição").fill("Notebook Agenda");
  await page.getByPlaceholder("Valor total").fill("1200");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/notebook agenda/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app");
  await expect(page.getByText(/compromissos futuros/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/internet agenda/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/notebook agenda/i).first()).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/saldo projetado/i)).toBeVisible({ timeout: 15000 });
});
