import { useState } from "react";
import type { FormEvent } from "react";
import { useCategories, useCategoryMutations } from "./hooks";
import { ApiError } from "../../lib/api";
import { Button, Field, PageHeader, useConfirm } from "../../components/ui";
import { labelOf, txTypeLabel } from "../../lib/labels";

export function CategoriesPage() {
  const [filter, setFilter] = useState("");
  const { data, isLoading } = useCategories(filter || undefined);
  const m = useCategoryMutations();
  const [name, setName] = useState("");
  const [type, setType] = useState("EXPENSE");
  const [msg, setMsg] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const confirm = useConfirm();

  async function onDelete(id: number, name: string) {
    setMsg("");
    const ok = await confirm.ask({
      title: "Excluir categoria?",
      body: `“${name}” será excluída. Lançamentos que a usam ficarão sem categoria.`,
      confirmLabel: "Excluir categoria",
    });
    if (!ok) return;
    try {
      await m.remove.mutateAsync(id);
    } catch {
      setMsg("Falha ao excluir.");
    }
  }

  async function onCreate(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    try {
      await m.create.mutateAsync({ name: name.trim(), type });
      setName("");
    } catch (e) {
      setMsg(e instanceof ApiError && e.status === 409 ? "Categoria já existe para este tipo." : "Falha ao criar.");
    }
  }

  return (
    <>
      <PageHeader title="Categorias" sub="Organize receitas e despesas." />
      {confirm.dialog}
      {msg && <p className="fw-error">{msg}</p>}
      <form onSubmit={onCreate} className="fw-row" style={{ alignItems: "flex-end" }}>
        <Field label="Nome da categoria">
          <input className="fw-input" style={{ width: "auto" }} placeholder="Ex.: Alimentação" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Tipo">
          <select className="fw-select" style={{ width: "auto" }} value={type} onChange={(e) => setType(e.target.value)}>
            <option value="EXPENSE">Despesa</option>
            <option value="INCOME">Receita</option>
          </select>
        </Field>
        <Button type="submit">Criar</Button>
      </form>
      {isLoading && <p>Carregando...</p>}
      <ul className="fw-list">
        {(data ?? []).map((c) => (
          <li className="fw-list-item" key={c.id}>
            {editing === c.id ? (
              <>
                <Field label="Novo nome">
                  <input className="fw-input" style={{ width: "auto" }} value={editName} onChange={(e) => setEditName(e.target.value)} />
                </Field>
                <Button size="sm" onClick={async () => { await m.patch.mutateAsync({ id: c.id, name: editName.trim() }); setEditing(null); }}>Salvar</Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancelar</Button>
              </>
            ) : (
              <>
                <span><strong>{c.name}</strong> ({labelOf(txTypeLabel, c.type)})</span>
                <Button size="sm" variant="ghost" onClick={() => { setEditing(c.id); setEditName(c.name); }}>Renomear</Button>
                <Button size="sm" variant="danger" onClick={() => onDelete(c.id, c.name)}>Excluir</Button>
              </>
            )}
          </li>
        ))}
      </ul>
      <div className="fw-row" style={{ marginTop: 16, alignItems: "flex-end" }}>
        <Field label="Filtrar por tipo">
          <select className="fw-select" style={{ width: "auto" }} value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">Todas</option>
            <option value="EXPENSE">Despesas</option>
            <option value="INCOME">Receitas</option>
          </select>
        </Field>
      </div>
    </>
  );
}
