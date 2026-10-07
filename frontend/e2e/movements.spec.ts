import { expect, test } from "@playwright/test";

// A criação das 4 operações é semeada via API (determinístico): o vaivém rápido
// de kinds no formulário já é coberto pelos testes de API; aqui o que importa é
// a visão unificada (lista, filtros, badge parcial). Fluxos via UI (contas,
// transferência, ativo) continuam exercitados abaixo.
test("movements: transferência + aporte + resgate + rendimento + reinvestimento em linhas únicas", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `mov_${uniq}@exemplo.com`;
  const password = "segredo-123";
  const ticker = `TST${uniq.slice(0, 4).toUpperCase()}`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Mov");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill(password);
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

  // transferência corrente → corretora (via UI)
  const fromRow = page.locator("li", { hasText: "Corrente E2E" }).first();
  await fromRow.getByRole("button", { name: /^transferir$/i }).click();
  await fromRow.locator("select").selectOption({ label: "Corretora E2E" });
  await fromRow.getByRole("textbox", { name: "Valor (R$)" }).fill("1000");
  await fromRow.getByRole("button", { name: /^enviar$/i }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: /^transferir$/i }).click();
  await expect(fromRow.getByText(/atual R\$ 4000\.00/i)).toBeVisible({ timeout: 15000 });

  // ativo via UI; operações via API
  await page.goto("/app/investments");
  await page.getByRole("textbox", { name: "Ticker" }).fill(ticker);
  await page.locator("form").first().locator("select").first().selectOption("OUTROS");
  await page.getByRole("textbox", { name: "Subtipo" }).fill("OUTRO");
  await page.getByLabel("Conta da corretora").selectOption({ label: "Corretora E2E" });
  const [assetResp] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/api/assets") && r.request().method() === "POST"),
    page.getByRole("button", { name: /^criar$/i }).click(),
  ]);
  const asset = await assetResp.json();
  const login = await page.request.post("/api/auth/login", { data: { email, password } });
  const token = (await login.json()).access_token;
  const headers = { Authorization: `Bearer ${token}` };
  const accs = await (await page.request.get("/api/accounts", { headers })).json();
  const corretora = accs.find((a: { name: string }) => a.name === "Corretora E2E").id;
  for (const body of [
    { kind: "APORTE", date: "2026-10-07", quantity: "10", price: "100" },
    { kind: "RENDIMENTO", date: "2026-10-07", amount: "50", account_id: corretora },
    { kind: "REINVESTIMENTO", date: "2026-10-07", quantity: "1", price: "100" },
    { kind: "RESGATE", date: "2026-10-07", quantity: "2", price: "110" },
  ]) {
    const r = await page.request.post(`/api/assets/${asset.id}/ops`, { data: body, headers });
    if (!r.ok()) throw new Error(`seed ${body.kind} falhou: ${r.status()} ${await r.text()}`);
  }

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

  // sem cotação em nenhum ativo: resumo parcial, total indisponível (nunca zero)
  await page.goto("/app/investments");
  await expect(page.getByText(/parcial/i).first()).toBeVisible({ timeout: 15000 });
});
