import { expect, test } from "@playwright/test";

test("dashboard: resumo reage a lançamentos e filtros", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `dash_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Dash");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/accounts");
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Conta Dash");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/conta dash/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/transactions");
  await page.locator("form").filter({ hasText: "Adicionar" }).locator("select").first().selectOption({ index: 1 });
  await page.getByPlaceholder("Ex.: Supermercado").fill("SALARIO DASH");
  await page.getByRole("textbox", { name: "Valor (R$)" }).fill("1000");
  await page.locator("form").filter({ hasText: "Adicionar" }).locator("select").nth(1).selectOption("INCOME");
  await page.getByRole("button", { name: /^adicionar$/i }).click();
  await expect(page.getByText(/salario dash/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app");
  await expect(page.getByText(/R\$\s1\.000,00/).first()).toBeVisible({ timeout: 15000 });

  // 5.x: pendência de categorização, variação vs mês anterior e contas com saldo
  await expect(page.getByText(/1 lançamento\(s\) sem categoria/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/sem base anterior/i).first()).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/atual R\$/i).first()).toBeVisible({ timeout: 15000 });

  // filtro que exclui o lançamento zera o resumo
  await page.getByLabel("De").fill("2020-01-01");
  await page.getByLabel("Até").fill("2020-01-31");
  await expect(page.getByText(/R\$\s0,00/).first()).toBeVisible({ timeout: 15000 });
});
