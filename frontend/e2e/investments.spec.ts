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
