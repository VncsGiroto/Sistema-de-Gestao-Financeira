# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: frontend/e2e/finance.spec.ts >> finance: conta + categoria + lançamento + categoria inline
- Location: frontend/e2e/finance.spec.ts:3:1

# Error details

```
Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
Call log:
  - navigating to "/register", waiting until "load"

```

# Test source

```ts
  1  | import { expect, test } from "@playwright/test";
  2  | 
  3  | test("finance: conta + categoria + lançamento + categoria inline", async ({ page }) => {
  4  |   const uniq = Date.now().toString(36);
  5  |   const email = `fin_${uniq}@exemplo.com`;
  6  | 
> 7  |   await page.goto("/register");
     |              ^ Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
  8  |   await page.getByPlaceholder("Nome").fill("Fin");
  9  |   await page.getByPlaceholder("E-mail").fill(email);
  10 |   await page.getByPlaceholder(/Senha/).fill("segredo-123");
  11 |   await page.getByRole("button", { name: /criar conta/i }).click();
  12 |   await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });
  13 | 
  14 |   // conta
  15 |   await page.goto("/app/accounts");
  16 |   await page.getByPlaceholder("Nome").fill("Corrente E2E");
  17 |   await page.getByPlaceholder("Banco").fill("Banco X");
  18 |   await page.getByPlaceholder("Saldo inicial").fill("100");
  19 |   await page.getByRole("button", { name: /^criar$/i }).click();
  20 |   await expect(page.getByText(/corrente e2e/i)).toBeVisible({ timeout: 15000 });
  21 | 
  22 |   // categoria
  23 |   await page.goto("/app/categories");
  24 |   await page.getByPlaceholder("Nome").fill(`Mercado ${uniq}`);
  25 |   await page.getByRole("button", { name: /^criar$/i }).click();
  26 |   await expect(page.getByText(new RegExp(`mercado ${uniq}`, "i"))).toBeVisible({ timeout: 15000 });
  27 | 
  28 |   // lançamento
  29 |   await page.goto("/app/transactions");
  30 |   await page.getByPlaceholder("Descrição").fill("SUPERMERCADO E2E");
  31 |   await page.getByPlaceholder("Valor").fill("42.50");
  32 |   await page.locator("form").filter({ hasText: "Adicionar" }).locator("select").first().selectOption({ index: 1 });
  33 |   await page.getByRole("button", { name: /^adicionar$/i }).click();
  34 |   await expect(page.getByText(/supermercado e2e/i)).toBeVisible({ timeout: 15000 });
  35 | 
  36 |   // filtro por conta: seleciona a conta e a linha continua visível
  37 |   const accountFilter = page.locator("select", { has: page.locator("option", { hasText: "Todas as contas" }) });
  38 |   await accountFilter.selectOption({ index: 1 });
  39 |   await expect(page.getByText(/supermercado e2e/i)).toBeVisible({ timeout: 15000 });
  40 |   await expect(page.getByText(/total: 1/i)).toBeVisible({ timeout: 15000 });
  41 | 
  42 |   // categoria inline: primeira linha, seleciona a categoria criada
  43 |   const catLabel = `Mercado ${uniq}`;
  44 |   const row = page.locator("tbody tr", { hasText: "SUPERMERCADO E2E" }).first();
  45 |   await row.locator("select").selectOption({ label: catLabel });
  46 |   await expect(row.locator("select option:checked")).toHaveText(catLabel, { timeout: 15000 });
  47 | });
  48 | 
```