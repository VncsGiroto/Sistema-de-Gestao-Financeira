import { useState } from "react";
import type { FormEvent } from "react";
import { useCategories, useCategoryMutations } from "./hooks";
import { ApiError } from "../../lib/api-client";

export function CategoriesPage() {
  const [filter, setFilter] = useState("");
  const { data, isLoading } = useCategories(filter || undefined);
  const m = useCategoryMutations();
  const [name, setName] = useState("");
  const [type, setType] = useState("EXPENSE");
  const [msg, setMsg] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

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
    <main style={{ fontFamily: "system-ui", padding: 32, maxWidth: 720 }}>
      <h1>Categorias</h1>
      {msg && <p style={{ color: "crimson" }}>{msg}</p>}
      <form onSubmit={onCreate} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="EXPENSE">Despesa</option>
          <option value="INCOME">Receita</option>
        </select>
        <button>Criar</button>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">Todas</option>
          <option value="EXPENSE">Despesas</option>
          <option value="INCOME">Receitas</option>
        </select>
      </form>
      {isLoading && <p>Carregando...</p>}
      <ul>
        {(data ?? []).map((c) => (
          <li key={c.id}>
            {editing === c.id ? (
              <>
                <input value={editName} onChange={(e) => setEditName(e.target.value)} />
                <button onClick={async () => { await m.patch.mutateAsync({ id: c.id, name: editName.trim() }); setEditing(null); }}>Salvar</button>
                <button onClick={() => setEditing(null)}>Cancelar</button>
              </>
            ) : (
              <>
                {c.name} ({c.type})
                <button onClick={() => { setEditing(c.id); setEditName(c.name); }}>Renomear</button>
                <button onClick={() => m.remove.mutateAsync(c.id)}>Excluir</button>
              </>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
