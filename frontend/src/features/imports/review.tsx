import { useState } from "react";
import { useAuth } from "../../lib/auth-store";
import { api } from "../../lib/api";
import type { ImportItem, Tx } from "../../lib/api";
import { ApiError } from "../../lib/api";
import { useImport, useImportItems, useImportMutations } from "./hooks";
import { useCategories } from "../finance/hooks";
import { Badge, Button, PageHeader, useConfirm, verdictTone } from "../../components/ui";
import { importStatusLabel, labelOf, txTypeLabel, verdictLabel } from "../../lib/labels";

function str(v: unknown): string {
  return typeof v === "string" ? v : v == null ? "—" : String(v);
}

function ItemRow({ item, decided, onDecide }: { item: ImportItem; decided: boolean; onDecide: (id: number, d: string) => void }) {
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
        {decided && <span> — decisão: {item.decision === "KEEP_BOTH" ? "manter" : "descartar"}</span>}
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
      {needsReview && !decided && (
        <p>
          <Button size="sm" onClick={() => onDecide(item.id, "KEEP_BOTH")}>Manter ambos</Button>{" "}
          <Button size="sm" variant="danger" onClick={() => onDecide(item.id, "DISCARD_IMPORTED")}>Descartar importado</Button>
        </p>
      )}
    </div>
  );
}

function CategorizeBatch({ importId }: { importId: number }) {
  const { access, refresh } = useAuth();
  const { data: categories } = useCategories();
  const [catId, setCatId] = useState("");
  const [msg, setMsg] = useState("");
  const [batch, setBatch] = useState<Tx[] | null>(null);

  async function load() {
    setMsg("");
    try {
      if (!access) return;
      const { data } = await api.authFetch<{ data: Tx[] }>(
        `/transactions?import_id=${importId}&per_page=100`, access, refresh,
      );
      setBatch(data.data);
    } catch {
      setMsg("Falha ao carregar lançamentos.");
    }
  }

  async function apply() {
    setMsg("");
    if (!catId || !access) return;
    const ids = (batch ?? []).filter((t) => t.category_id == null).map((t) => t.id);
    if (!ids.length) return;
    try {
      const res = await api.authed((t) => api.txs.categorize({ ids, category_id: Number(catId) }, t), access, refresh);
      setMsg(`Categorizados ${res.updated} · ignorados por tipo ${res.skipped_type}.`);
      await load();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao categorizar.");
    }
  }

  const pending = (batch ?? []).filter((t) => t.category_id == null);
  return (
    <section className="fw-card" style={{ marginTop: 16 }}>
      <h2>Categorização em massa</h2>
      {batch == null ? (
        <Button size="sm" onClick={load}>Carregar lançamentos importados</Button>
      ) : (
        <>
          <p>{pending.length} sem categoria de {batch.length} importados.</p>
          {pending.length > 0 && (
            <div className="fw-row">
              <select className="fw-select" style={{ width: "auto" }} aria-label="Categoria para aplicar em massa" value={catId} onChange={(e) => setCatId(e.target.value)}>
                <option value="">Categoria...</option>
                {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name} ({labelOf(txTypeLabel, c.type)})</option>)}
              </select>
              <Button size="sm" onClick={apply}>Aplicar a {pending.length}</Button>
            </div>
          )}
        </>
      )}
      {msg && <p>{msg}</p>}
    </section>
  );
}

export function ReviewPage({ id }: { id: number }) {
  const { data: imp } = useImport(id);
  const [verdict, setVerdict] = useState("");
  const { data: items } = useImportItems(id, verdict || undefined);
  const { data: allItems } = useImportItems(id);
  const m = useImportMutations(id);
  const [msg, setMsg] = useState("");
  const [result, setResult] = useState("");
  const [committed, setCommitted] = useState(false);
  const confirm = useConfirm();

  const list = allItems ?? [];
  const count = (v: string) => list.filter((i) => i.verdict === v).length;
  const pending = list.filter(
    (i) => (i.verdict === "EXACT_DUPLICATE" || i.verdict === "FUZZY_CANDIDATE") && !i.decision,
  );
  const decidedDiscard = list.filter((i) => i.decision === "DISCARD_IMPORTED").length;
  const willImport = count("NEW") + list.filter((i) => i.decision === "KEEP_BOTH").length;
  const processing = imp?.status === "RECEIVED" || imp?.status === "PROCESSING";
  const ready = imp?.status === "VALIDATED";

  async function decide(items_: { item_id: number; decision: string }[]) {
    setMsg("");
    try {
      await m.review.mutateAsync(items_);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha ao decidir.");
    }
  }

  async function decideAll(decision: string) {
    const ok = await confirm.ask({
      title: decision === "KEEP_BOTH" ? "Manter todas?" : "Descartar todas?",
      body: `${pending.length} duplicatas pendentes serão ${decision === "KEEP_BOTH" ? "mantidas junto com os originais" : "descartadas"}.`,
      confirmLabel: decision === "KEEP_BOTH" ? "Manter todas" : "Descartar todas",
    });
    if (ok) await decide(pending.map((i) => ({ item_id: i.id, decision })));
  }

  async function commit() {
    setMsg(""); setResult("");
    try {
      const r = await m.commit.mutateAsync();
      setResult(`Importados ${r.imported_rows}, duplicados ${r.duplicate_rows}, pulados ${r.skipped}.`);
      setCommitted(true);
    } catch (e) {
      setMsg(e instanceof ApiError && e.status === 409
        ? "Há itens aguardando revisão."
        : "Falha ao confirmar.");
    }
  }

  return (
    <>
      <PageHeader title={`Revisão da importação #${id}`} sub="Resumo → duplicatas → categorização → confirmação." backTo="/app/imports" />
      {confirm.dialog}
      {imp && <p>Status: <Badge tone={verdictTone(imp.status)}>{labelOf(importStatusLabel, imp.status)}</Badge> — total {imp.total_rows}, importados {imp.imported_rows}, duplicados {imp.duplicate_rows}</p>}
      {processing && <p>Processando extrato… a página atualiza sozinha.</p>}
      {imp?.error && <p className="fw-error">{imp.error}</p>}
      {msg && <p className="fw-error">{msg}</p>}
      {result && <p>{result}</p>}

      <section className="fw-card" style={{ marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>Resumo</h2>
        <p>Novos {count("NEW")} · duplicados exatos {count("EXACT_DUPLICATE")} · possíveis {count("FUZZY_CANDIDATE")} · inválidos {count("INVALID")} · aguardando decisão {pending.length}.</p>
        {pending.length > 0 && (
          <div className="fw-row">
            <Button size="sm" onClick={() => decideAll("KEEP_BOTH")}>Manter todas</Button>
            <Button size="sm" variant="danger" onClick={() => decideAll("DISCARD_IMPORTED")}>Descartar todas</Button>
          </div>
        )}
      </section>

      <div className="fw-row">
        <select className="fw-select" style={{ width: "auto" }} aria-label="Filtrar por veredito" value={verdict} onChange={(e) => setVerdict(e.target.value)}>
          <option value="">Todos</option>
          <option value="NEW">Novos</option>
          <option value="EXACT_DUPLICATE">Duplicados exatos</option>
          <option value="FUZZY_CANDIDATE">Possíveis duplicatas</option>
          <option value="INVALID">Inválidos</option>
        </select>
        <Button
          onClick={commit}
          disabled={!ready || pending.length > 0}
        >
          {pending.length > 0
            ? `Faltam ${pending.length} decisões`
            : `Confirmar importação: ${willImport} lançamentos · ${decidedDiscard} descartadas`}
        </Button>
      </div>
      {(items ?? []).map((it) => (
        <ItemRow
          key={it.id}
          item={it}
          decided={!!it.decision}
          onDecide={(item_id, decision) => decide([{ item_id, decision }])}
        />
      ))}

      {committed && <CategorizeBatch importId={id} />}
    </>
  );
}
