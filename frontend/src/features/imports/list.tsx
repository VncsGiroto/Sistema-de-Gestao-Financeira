import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAccounts } from "../finance/hooks";
import { ApiError } from "../../lib/api-client";
import { useImportMutations, useImports } from "./hooks";

export function ImportsPage() {
  const { data, isLoading } = useImports();
  const { data: accounts } = useAccounts();
  const m = useImportMutations(0);
  const navigate = useNavigate();
  const [accountId, setAccountId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [msg, setMsg] = useState("");

  async function onUpload(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    if (!accountId) return setMsg("Selecione uma conta.");
    if (!file) return setMsg("Selecione um arquivo .ofx.");
    try {
      const res = await m.upload.mutateAsync({ account_id: Number(accountId), file });
      navigate({ to: "/app/imports/$id", params: { id: String(res.import_id) } });
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Falha no upload.");
    }
  }

  return (
    <main style={{ fontFamily: "system-ui", padding: 32, maxWidth: 720 }}>
      <h1>Importações OFX</h1>
      {msg && <p style={{ color: "crimson" }}>{msg}</p>}
      <form onSubmit={onUpload} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          <option value="">Conta...</option>
          {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <input type="file" accept=".ofx,.qfx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button>Enviar</button>
      </form>
      {isLoading && <p>Carregando...</p>}
      <ul>
        {(data ?? []).map((i) => (
          <li key={i.id}>
            <button onClick={() => navigate({ to: "/app/imports/$id", params: { id: String(i.id) } })}>
              #{i.id} {i.file_name}
            </button>{" "}
            — {i.status} (total {i.total_rows}, importados {i.imported_rows}, duplicados {i.duplicate_rows})
            {i.error && <span style={{ color: "crimson" }}> — {i.error}</span>}
          </li>
        ))}
      </ul>
    </main>
  );
}
