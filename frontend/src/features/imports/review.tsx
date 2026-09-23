import { useState } from "react";
import { useAuth } from "../../lib/auth-store";
import { api } from "../../lib/api-client";
import type { ImportItem, Tx } from "../../lib/api-client";
import { ApiError } from "../../lib/api-client";
import { useImport, useImportItems, useImportMutations } from "./hooks";

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
    <div style={{ border: "1px solid #ccc", margin: "8px 0", padding: 8 }}>
      <p>
        <strong>#{item.row_no}</strong> {str(p.date)} — {str(p.description)} — R$ {str(p.amount)} ({str(p.type)})
        {" "}→ <em>{item.verdict}</em>
        {typeof p.score === "number" && <span> (score {p.score})</span>}
      </p>
      {item.matched_transaction_id && (
        <>
          <button onClick={toggle}>{open ? "Ocultar original" : "Ver original no banco"}</button>
          {open && (
            matched ? (
              <p>Banco: {matched.date} — {matched.description} — R$ {matched.amount} ({matched.type})</p>
            ) : <p>Carregando original...</p>
          )}
        </>
      )}
      {needsReview && (
        <p>
          <button onClick={() => onDecide(item.id, "KEEP_BOTH")}>Manter ambos</button>{" "}
          <button onClick={() => onDecide(item.id, "DISCARD_IMPORTED")}>Descartar importado</button>
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
    <main style={{ fontFamily: "system-ui", padding: 32 }}>
      <h1>Revisão da importação #{id}</h1>
      {imp && <p>Status: {imp.status} — total {imp.total_rows}, importados {imp.imported_rows}, duplicados {imp.duplicate_rows}</p>}
      {imp?.error && <p style={{ color: "crimson" }}>{imp.error}</p>}
      {msg && <p style={{ color: "crimson" }}>{msg}</p>}
      {result && <p>{result}</p>}
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <select value={verdict} onChange={(e) => setVerdict(e.target.value)}>
          <option value="">Todos</option>
          <option value="NEW">Novos</option>
          <option value="EXACT_DUPLICATE">Duplicados exatos</option>
          <option value="FUZZY_CANDIDATE">Possíveis duplicatas</option>
          <option value="INVALID">Inválidos</option>
        </select>
        <button onClick={commit}>Confirmar importação</button>
      </div>
      {(items ?? []).map((it) => <ItemRow key={it.id} item={it} onDecide={decide} />)}
    </main>
  );
}
