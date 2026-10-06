import { expect, test } from "@playwright/test";

test("movements: transferência + aporte + resgate + rendimento + reinvestimento em linhas únicas", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `mov_${uniq}@exemplo.com`;
  const ticker = `TST${uniq.slice(0, 4).toUpperCase()}`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Mov");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  // contas: corrente financiada + corretora zerada
  await page.goto("/app/accounts");
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Corrente E2E");
  await page.getByRole("textbox", { name: /^saldo inicial/i }).fill("5000");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/corrente e2e/i)).toBeVisible({ timeout: 15000 });
  await page.getByRole("textbox", { name: "Nome da conta" }).fill("Corretora E2E");
  await page.locator("form").locator("select").first().selectOption("INVESTMENT");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/corretora e2e/i)).toBeVisible({ timeout: 15000 });

  // transferência corrente → corretora
  const fromRow = page.locator("li", { hasText: "Corrente E2E" }).first();
  await fromRow.getByRole("button", { name: /^transferir$/i }).click();
  await fromRow.locator("select").selectOption({ label: "Corretora E2E" });
  await fromRow.getByRole("textbox", { name: "Valor (R$)" }).fill("1000");
  await fromRow.getByRole("button", { name: /^enviar$/i }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: /^transferir$/i }).click();
  await expect(fromRow.getByText(/atual R\$ 4000\.00/i)).toBeVisible({ timeout: 15000 });

  // ativo + operações
  await page.goto("/app/investments");
  await page.getByRole("textbox", { name: "Ticker" }).fill(ticker);
  await page.locator("form").first().locator("select").first().selectOption("OUTROS");
  await page.getByRole("textbox", { name: "Subtipo" }).fill("OUTRO");
  await page.getByLabel("Conta da corretora").selectOption({ label: "Corretora E2E" });
  await page.getByRole("button", { name: /^criar$/i }).click();
  await page.getByRole("button", { name: /detalhar/i }).click();

  async function lancar(kind: string, fields: Record<string, string>, account?: string, n?: number) {
    await page.getByLabel("Operação").selectOption(kind);
    for (const [name, value] of Object.entries(fields)) {
      await page.getByRole("textbox", { name }).fill(value);
    }
    if (account) await page.getByLabel("Conta de destino").selectOption({ label: account });
    await page.getByRole("button", { name: /^lançar$/i }).click();
    if (n) await expect(page.getByText(new RegExp(`histórico de operações \\(${n}\\)`, "i"))).toBeVisible({ timeout: 15000 });
  }

  await lancar("APORTE", { "Quantidade de cotas": "10", "Preço por cota (R$)": "100" }, undefined, 1);
  await page.getByRole("textbox", { name: "Preço manual (R$)" }).fill("110");
  await page.getByRole("button", { name: /precificar/i }).click();
  await lancar("RENDIMENTO", { "Valor do rendimento (R$)": "50" }, "Corretora E2E", 2);
  await lancar("REINVESTIMENTO", { "Quantidade de cotas": "1", "Preço por cota (R$)": "100" }, undefined, 3);
  await lancar("RESGATE", { "Quantidade de cotas": "2", "Preço por cota (R$)": "110" }, undefined, 4);

  // visão unificada: uma linha por evento
  await page.goto("/app/transactions");
  await expect(page.getByText(/total: 5/i)).toBeVisible({ timeout: 15000 });
  for (const kind of ["Transferência", "Aporte", "Resgate", "Rendimento", "Reinvestimento"]) {
    await expect(page.getByRole("cell", { name: kind }).first()).toBeVisible({ timeout: 15000 });
  }
  await expect(page.getByText(/sem efeito no caixa/i).first()).toBeVisible();
  await expect(page.getByText(/via operação/i).first()).toBeVisible();

  // filtro por tipo: só transferência
  await page.getByText("Filtros", { exact: true }).click();
  await page.locator("details").getByLabel("Tipo").selectOption("TRANSFER");
  await expect(page.getByText(/total: 1/i)).toBeVisible({ timeout: 15000 });
  await page.locator("details").getByLabel("Tipo").selectOption("");

  // filtro por conta: corretora vê tudo (entrada, saída e neutro); corrente só a saída
  const accountFilter = page.locator("select", { has: page.locator("option", { hasText: "Todas as contas" }) });
  await accountFilter.selectOption({ label: "Corretora E2E" });
  await expect(page.getByText(/total: 5/i)).toBeVisible({ timeout: 15000 });
  await accountFilter.selectOption({ label: "Corrente E2E" });
  await expect(page.getByText(/total: 1/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/saída/i).first()).toBeVisible();
});
