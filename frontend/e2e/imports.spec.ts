import { expect, test } from "@playwright/test";
import { fileURLToPath } from "url";
import path from "path";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OFX = path.resolve(HERE, "../../backend/tests/fixtures/duplicado.ofx");

test("import → review → commit", async ({ page }) => {
  const uniq = Date.now().toString(36);
  const email = `imp_${uniq}@exemplo.com`;

  await page.goto("/register");
  await page.getByPlaceholder("Nome").fill("Imp");
  await page.getByPlaceholder("E-mail").fill(email);
  await page.getByPlaceholder(/Senha/).fill("segredo-123");
  await page.getByRole("button", { name: /criar conta/i }).click();
  await expect(page.getByText(/bem-vindo/i)).toBeVisible({ timeout: 15000 });

  await page.goto("/app/accounts");
  await page.getByPlaceholder("Nome").fill("Corrente Imp");
  await page.getByRole("button", { name: /^criar$/i }).click();
  await expect(page.getByText(/corrente imp/i)).toBeVisible({ timeout: 15000 });

  // upload
  await page.goto("/app/imports");
  await page.locator("form select").selectOption({ index: 1 });
  await page.locator('input[type="file"]').setInputFiles(OFX);
  await page.getByRole("button", { name: /enviar/i }).click();
  await expect(page.getByText(/revisão da importação/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/VALIDATED/)).toBeVisible({ timeout: 20000 });

  // itens NEW aparecem; commit direto (sem pendências) importa
  await expect(page.getByText(/SUPERMERCADO XYZ/)).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: /confirmar importação/i }).click();
  await expect(page.getByText("Importados 2, duplicados 0, pulados 0.")).toBeVisible({ timeout: 15000 });

  // lançamento aparece no extrato
  await page.goto("/app/transactions");
  await expect(page.getByText(/supermercado xyz/i).first()).toBeVisible({ timeout: 15000 });
});
