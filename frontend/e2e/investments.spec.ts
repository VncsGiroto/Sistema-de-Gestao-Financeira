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

  await page.goto("/app/accounts");
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Corretora E2E");
  await page.locator("form").locator("select").first().selectOption("INVESTMENT");
  await page.getByRole("textbox", { name: /^saldo inicial/i }).fill("2000");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/corretora e2e/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/investments");
  await page.getByRole("textbox", { name: "Ticker" }).fill(`TST${uniq.slice(0, 4).toUpperCase()}`);
  await page.locator("form").first().locator("select").first().selectOption("OUTROS");
  await page.getByRole("textbox", { name: "Subtipo" }).fill("OUTRO");
  await page.getByLabel("Conta da corretora").selectOption({ label: "Corretora E2E" });
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(new RegExp(`tst${uniq.slice(0, 4)}`, "i"))).toBeVisible({ timeout: 15000 });

  // detalha, aporta e precifica
  await page.getByRole("button", { name: /detalhar/i }).click();
  await page.getByRole("textbox", { name: "Quantidade de cotas" }).fill("10");
  await page.getByRole("textbox", { name: "Preço por cota (R$)" }).fill("100");
  await page.getByRole("button", { name: /^lançar$/i }).click();
  await page.getByRole("textbox", { name: "Preço manual (R$)" }).fill("120");
  await page.getByRole("button", { name: /precificar/i }).click();
  await expect(page.getByText(/P&L/i)).toBeVisible({ timeout: 15000 });
  // /returns aguarda fail-open dos benchmarks (BCB público): latência fria pode
  // estourar 15s na primeira chamada; valores não importam, só a presença.
  await expect(page.getByText(/XIRR/i)).toBeVisible({ timeout: 60000 });

  // carteira consolidada: caixa zerado pelo aporte, total avaliado, histórico registrado
  await expect(page.getByText(/caixa nas corretoras/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/histórico de operações \(1\)/i)).toBeVisible({ timeout: 15000 });

  // histórico lista o aporte; excluir com confirmação recalcula a posição
  await expect(page.getByText(/histórico de operações \(1\)/i)).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: /^excluir$/i }).last().click();
  await page.getByRole("alertdialog").getByRole("button", { name: /excluir operação/i }).click();
  await expect(page.getByText(/histórico de operações \(0\)/i)).toBeVisible({ timeout: 15000 });
});

test("investments: RF com contrato opera em valor, sem cota", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `rfv_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Rfv");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/accounts");
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Corretora RF");
  await page.locator("form").locator("select").first().selectOption("INVESTMENT");
  await page.getByRole("textbox", { name: /^saldo inicial/i }).fill("2000");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/corretora rf/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/investments");
  await page.getByRole("textbox", { name: "Ticker" }).fill(`CDB${uniq.slice(0, 4).toUpperCase()}`);
  await page.locator("form").first().locator("select").first().selectOption("RENDA_FIXA");
  await page.getByLabel("Conta da corretora").selectOption({ label: "Corretora RF" });
  await page.getByLabel("Contrato").selectOption("CDI_PCT");
  await page.getByRole("textbox", { name: /percentual do cdi/i }).fill("100");
  await page.getByRole("button", { name: /^criar$/i }).click();
  const rfvTicker = `CDB${uniq.slice(0, 4).toUpperCase()}`;
  await expect(page.getByText(new RegExp(rfvTicker, "i"))).toBeVisible({ timeout: 15000 });
  const rfvRow = page.locator("li", { hasText: new RegExp(rfvTicker, "i") });
  await expect(rfvRow.getByText(/sem conta vinculada/i)).toHaveCount(0, { timeout: 15000 });

  // detalha e aporta em reais (primeiro aporte usa cotação 1, sem BCB)
  await page.getByRole("button", { name: /detalhar/i }).click();
  const rfvForm = page.locator("form", { has: page.getByRole("button", { name: /^lançar$/i }) });
  await rfvForm.getByRole("textbox", { name: "Valor (R$)" }).fill("1000");
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/ops") && r.request().method() === "POST"),
    rfvForm.getByRole("button", { name: /^lançar$/i }).click(),
  ]);
  if (resp.status() !== 201) throw new Error(`aporte RF falhou: ${resp.status()}`);
  await expect(page.getByText(/aplicado R\$\s1\.000,00/i)).toBeVisible({ timeout: 15000 });
});
