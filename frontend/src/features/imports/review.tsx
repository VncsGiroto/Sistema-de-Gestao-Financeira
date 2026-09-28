import { useState } from "react";
import { useAuth } from "../../lib/auth-store";
import { api } from "../../lib/api";
import type { ImportItem, Tx } from "../../lib/api";
import { ApiError } from "../../lib/api";
import { useImport, useImportItems, useImportMutations } from "./hooks";
import { Badge, Button, PageHeader, verdictTone } from "../../components/ui";
import { importStatusLabel, labelOf, txTypeLabel, verdictLabel } from "../../lib/labels";

function str(v: unknown): string {
  return typeof v === "string" ? v : v == null ? "—" : String(v);
}

function ItemRow({ item, onDecide }: { item: ImportItem; onDecide: (id: number, d: string) => void }) {
  const { access } = useAuth();
  const [matched, setMatched] = useState<Tx | null>(null);
  const [open, setOpen] = useState(false);
  const p = item.payload as Record<string, string>;

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && item.matched_transaction_id && access && !matched) {
      try {
        setMatched(await api.imports.matched(item.matched_transaction_id, access));
      } catch { /* sem sessão */ }
    }
  }

  const needsReview = item.verdict === "EXACT_DUPLICATE" || item.verdict === "FUZZY_CANDIDATE";
  return (
    <div className="fw-card" style={{ marginBottom: 8 }}>
      <p>
        <strong>#{item.row_no}</strong> {str(p.date)} — {str(p.description)} — R$ {str(p.amount)} ({labelOf(txTypeLabel, str(p.type))})
        {" "}<Badge tone={verdictTone(item.verdict)}>{labelOf(verdictLabel, item.verdict)}</Badge>
        {typeof p.score === "number" && <span> (score {p.score})</span>}
      </p>
      {item.matched_transaction_id && (
        <>
          <Button size="sm" variant="ghost" onClick={toggle}>{open ? "Ocultar original" : "Ver original no banco"}</Button>
          {open && (
            matched ? (
              <p>Banco: {matched.date} — {matched.description} — R$ {matched.amount} ({labelOf(txTypeLabel, matched.type)})</p>
            ) : <p>Carregando original...</p>
          )}
        </>
      )}
      {needsReview && (
        <p>
          <Button size="sm" onClick={() => onDecide(item.id, "KEEP_BOTH")}>Manter ambos</Button>{" "}
          <Button size="sm" variant="danger" onClick={() => onDecide(item.id, "DISCARD_IMPORTED")}>Descartar importado</Button>
        </p>
      )}
    </div>
  );
}

export function ReviewPage({ id }: { id: number }) {
  const { data: imp } = useImport(id);
  const [verdict, setVerdict] = useState("");
  const { data: items } = useImportItems(id, verdict || undefined);
  const m = useImportMutations(id);
  const [msg, setMsg] = useState("");
  const [result, setResult] = useState("");

  async function decide(item_id: number, decision: string) {
    setMsg("");
    try {
      await m.review.mutateAsync([{ item_id, decision }]);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao decidir.");
    }
  }

  async function commit() {
    setMsg(""); setResult("");
    try {
      const r = await m.commit.mutateAsync();
      setResult(`Importados ${r.imported_rows}, duplicados ${r.duplicate_rows}, pulados ${r.skipped}.`);
    } catch (e) {
      setMsg(e instanceof ApiError && e.status === 409
        ? "Há itens aguardando revisão."
        : "Falha ao confirmar.");
    }
  }

  return (
    <>
      <PageHeader title={`Revisão da importação #${id}`} sub="Confirme duplicatas e importe os lançamentos." backTo="/app/imports" />
      {imp && <p>Status: <Badge tone={verdictTone(imp.status)}>{labelOf(importStatusLabel, imp.status)}</Badge> — total {imp.total_rows}, importados {imp.imported_rows}, duplicados {imp.duplicate_rows}</p>}
      {imp?.error && <p className="fw-error">{imp.error}</p>}
      {msg && <p className="fw-error">{msg}</p>}
      {result && <p>{result}</p>}
      <div className="fw-row">
        <select className="fw-select" style={{ width: "auto" }} value={verdict} onChange={(e) => setVerdict(e.target.value)}>
          <option value="">Todos</option>
          <option value="NEW">Novos</option>
          <option value="EXACT_DUPLICATE">Duplicados exatos</option>
          <option value="FUZZY_CANDIDATE">Possíveis duplicatas</option>
          <option value="INVALID">Inválidos</option>
        </select>
        <Button onClick={commit}>Confirmar importação</Button>
      </div>
      {(items ?? []).map((it) => <ItemRow key={it.id} item={it} onDecide={decide} />)}
    </>
  );
}
