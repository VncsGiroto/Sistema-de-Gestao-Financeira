import { useState } from "react";
import { assetClassLabel, labelOf } from "../../lib/labels";
import { Field, PageHeader, useConfirm } from "../../components/ui";
import { useAccounts } from "../finance/hooks";
import { useAssetMutations, useAssets, usePortfolio } from "./hooks";
import { PortfolioSummary } from "./components/PortfolioSummary";
import { AssetCreateForm } from "./components/AssetCreateForm";
import { AssetList } from "./components/AssetList";

const CLASSES = ["RENDA_FIXA", "RENDA_VARIAVEL", "FUNDOS", "CRIPTO", "OUTROS"] as const;

export function InvestmentsPage() {
  const [cls, setCls] = useState("");
  const { data, isLoading } = useAssets(cls || undefined);
  const { data: pf } = usePortfolio();
  const m = useAssetMutations();
  const [msg, setMsg] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const confirm = useConfirm();
  const { data: accounts } = useAccounts();

  async function onDelete(id: number, ticker: string) {
    setMsg("");
    const ok = await confirm.ask({
      title: "Excluir ativo?",
      body: `“${ticker}” e todo o seu histórico de operações serão excluídos. Rendimentos espelhados no extrato também serão removidos.`,
      confirmLabel: "Excluir ativo",
    });
    if (!ok) return;
    try {
      await m.remove.mutateAsync(id);
    } catch {
      setMsg("Falha ao excluir.");
    }
  }

  return (
    <>
      <PageHeader title="Investimentos" sub="Ativos, operações, posição e rentabilidade." />
      {msg && <p className="fw-error">{msg}</p>}
      {confirm.dialog}
      {pf && <PortfolioSummary pf={pf} />}
      <AssetCreateForm onError={setMsg} />
      {isLoading && <p>Carregando...</p>}
      {!isLoading && (data ?? []).length === 0 && <p>Nenhum ativo ainda — crie o primeiro acima.</p>}
      <AssetList assets={data ?? []} accounts={accounts} openId={openId} onToggle={(id) => setOpenId(openId === id ? null : id)} onDelete={onDelete} />
      <div className="fw-row" style={{ marginTop: 16, alignItems: "flex-end" }}>
        <Field label="Filtrar por classe">
          <select className="fw-select" style={{ width: "auto" }} value={cls} onChange={(e) => setCls(e.target.value)}>
            <option value="">Todas as classes</option>
            {CLASSES.map((c) => (
              <option key={c} value={c}>
                {labelOf(assetClassLabel, c)}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </>
  );
}
