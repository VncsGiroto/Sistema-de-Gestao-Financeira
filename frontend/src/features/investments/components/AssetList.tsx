import { assetClassLabel, labelOf } from "../../../lib/labels";
import { Badge, Button } from "../../../components/ui";
import type { Asset } from "../../../lib/api";
import type { Account } from "../../../lib/api";
import { AssetDetail } from "./AssetDetail";

type Props = {
  assets: Asset[];
  accounts: Account[] | undefined;
  openId: number | null;
  onToggle: (id: number) => void;
  onDelete: (id: number, ticker: string) => void;
};

export function AssetList({ assets, accounts, openId, onToggle, onDelete }: Props) {
  if (assets.length === 0) {
    return <p>Nenhum ativo ainda — crie o primeiro acima.</p>;
  }
  return (
    <>
      <h2>Ativos</h2>
      <ul className="fw-list">
        {assets.map((a) => (
          <li className="fw-list-item" key={a.id}>
            <span>
              {a.ticker} <Badge>{labelOf(assetClassLabel, a.asset_class)}</Badge>{" "}
              {a.account_id ? (accounts ?? []).find((c) => c.id === a.account_id)?.name ?? "" : <Badge tone="amber">sem conta vinculada</Badge>}
            </span>
            <span>
              <Button size="sm" variant="ghost" onClick={() => onToggle(a.id)}>
                Detalhar
              </Button>{" "}
              <Button size="sm" variant="danger" onClick={() => onDelete(a.id, a.ticker)}>
                Excluir
              </Button>
            </span>
            {openId === a.id && <AssetDetail asset={a} />}
          </li>
        ))}
      </ul>
    </>
  );
}
