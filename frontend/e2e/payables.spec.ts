import { expect, test } from "@playwright/test";

test("payables: criar FIXA + baixar e ver transação", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `pay_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Pay");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/accounts");
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Corrente Pay");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/corrente pay/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/payables");
  await page.getByRole("textbox", { name: "Descrição" }).fill("Internet Pay");
  await page.getByRole("textbox", { name: "Valor mensal (R$)" }).fill("120");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/internet pay/i)).toBeVisible({ timeout: 15000 });

  // baixa: seleciona a conta, confirma no diálogo e baixa
  await page.getByRole("button", { name: /^pagar$/i }).click();
  await page.locator("form").filter({ hasText: "Baixar" }).locator("select").first().selectOption({ index: 1 });
  await page.getByRole("button", { name: /^baixar$/i }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: /^baixar$/i }).click();
  await expect(page.getByText(/baixado/i)).toBeVisible({ timeout: 15000 });

  // detalhe: explicação do conceito + histórico com a baixa lançada
  await page.getByRole("button", { name: /^detalhar$/i }).click();
  await expect(page.getByText(/histórico de baixas \(1\)/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/valor igual todo mês/i)).toBeVisible({ timeout: 15000 });

  // excluir conta com baixa lançada é bloqueado, com explicação
  await page.getByRole("button", { name: /^excluir$/i }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: /^excluir$/i }).click();
  await expect(page.getByText(/não pode ser excluída/i)).toBeVisible({ timeout: 15000 });

  // transação aparece no extrato
  await page.goto("/app/transactions");
  await expect(page.getByText(/internet pay/i).first()).toBeVisible({ timeout: 15000 });
});

test("payables: parcelada com desconto antecipando", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `pa2_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Pa2");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/accounts");
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Conta Pa2");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/conta pa2/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/payables");
  await page.locator("form").first().locator("select").first().selectOption("INSTALLMENT");
  await page.getByRole("textbox", { name: "Descrição" }).fill("Curso Pay");
  await page.getByRole("textbox", { name: "Valor total (R$)" }).fill("1000");
  const firstDue = new Date(Date.now() + 10 * 864e5).toISOString().slice(0, 10);
  await page.locator("form").first().locator('input[type="date"]').fill(firstDue);
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/curso pay/i)).toBeVisible({ timeout: 15000 });

  // marca parcelas 2 e 3 + desconto e baixa
  await page.getByRole("button", { name: /^pagar$/i }).click();
  const box = page.locator("form").filter({ hasText: "Baixar" });
  await box.locator("select").first().selectOption({ index: 1 });
  await box.getByText(/^2 \(R\$/).click();
  await box.getByText(/^3 \(R\$/).click();
  await box.getByPlaceholder("Desconto").fill("100");
  await page.getByRole("button", { name: /^baixar$/i }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: /^baixar$/i }).click();
  await expect(page.getByText(/baixado/i)).toBeVisible({ timeout: 15000 });
});
