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
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Corrente E2E");
  await page.getByRole("textbox", { name: "Banco" }).fill("Banco X");
  await page.getByRole("textbox", { name: /^saldo inicial/i }).fill("100");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/corrente e2e/i)).toBeVisible({ timeout: 15000 });

  // categoria
  await page.goto("/app/categories");
  await page.getByRole("textbox", { name: "Nome da categoria" }).fill(`Mercado ${uniq}`);
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(new RegExp(`mercado ${uniq}`, "i"))).toBeVisible({ timeout: 15000 });

  // lançamento
  await page.goto("/app/transactions");
  await page.getByPlaceholder("Ex.: Supermercado").fill("SUPERMERCADO E2E");
  await page.getByRole("textbox", { name: "Valor (R$)" }).fill("42.50");
  await page.locator("form").filter({ hasText: "Adicionar" }).locator("select").first().selectOption({ index: 1 });
  await page.getByRole("button", { name: /^adicionar$/i }).click();
  await expect(page.getByText(/supermercado e2e/i)).toBeVisible({ timeout: 15000 });

  // filtro por conta: abre os filtros, seleciona a conta e a linha continua visível
  await page.getByText("Filtros", { exact: true }).click();
  const accountFilter = page.locator("select", { has: page.locator("option", { hasText: "Todas as contas" }) });
  await accountFilter.selectOption({ index: 1 });
  await expect(page.getByText(/supermercado e2e/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/total: 1/i)).toBeVisible({ timeout: 15000 });

  // categoria inline: primeira linha, seleciona a categoria criada
  const catLabel = `Mercado ${uniq}`;
  const row = page.locator("tbody tr", { hasText: "SUPERMERCADO E2E" }).first();
  await row.locator("select").selectOption({ label: catLabel });
  await expect(row.locator("select option:checked")).toHaveText(catLabel, { timeout: 15000 });

  // transferência entre contas: debita uma, credita outra, sem virar receita/despesa
  await page.goto("/app/accounts");
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Destino E2E");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/destino e2e/i)).toBeVisible({ timeout: 15000 });
  const fromRow = page.locator("li", { hasText: "Corrente E2E" }).first();
  await fromRow.getByRole("button", { name: /^transferir$/i }).click();
  await fromRow.locator("select").selectOption({ label: "Destino E2E" });
  await fromRow.getByRole("textbox", { name: "Valor (R$)" }).fill("7.50");
  await fromRow.getByRole("button", { name: /^enviar$/i }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: /^transferir$/i }).click();
  await expect(fromRow.getByText(/atual R\$ 50\.00/i)).toBeVisible({ timeout: 15000 });
  const toRow = page.locator("li", { has: page.locator("strong", { hasText: "Destino E2E" }) });
  await expect(toRow.getByText(/atual R\$ 7\.50/i)).toBeVisible({ timeout: 15000 });
});
