import { pct } from "../lib/formatters";
import type { Returns } from "../../../lib/api";

export function ReturnsCard({ ret }: { ret: Returns | undefined }) {
  if (!ret || (ret.simple == null && ret.xirr == null && ret.twr == null)) return null;
  return (
    <p>
      Simples {pct(ret.simple)} · XIRR {pct(ret.xirr)} ·{" "}
      <span title="Apreciação da cotação; exclui proventos reinvestidos">TWR de preço {pct(ret.twr)}</span> ({pct(ret.twr_annualized)} a.a.)
      {ret.benchmarks && (
        <>
          {" "}
          · CDI {pct(ret.benchmarks.cdi)} · IPCA {pct(ret.benchmarks.ipca)}
        </>
      )}
    </p>
  );
}
