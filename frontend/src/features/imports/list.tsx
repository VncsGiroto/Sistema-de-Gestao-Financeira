import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAccounts } from "../finance/hooks";
import { ApiError } from "../../lib/api";
import { importStatusLabel, labelOf } from "../../lib/labels";
import { useImportMutations, useImports } from "./hooks";
import { Badge, Button, PageHeader, verdictTone } from "../../components/ui";

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
    <>
      <PageHeader title="Importações OFX" sub="Envie extratos e acompanhe o processamento." />
      {msg && <p className="fw-error">{msg}</p>}
      <form onSubmit={onUpload} className="fw-row">
        <select className="fw-select" style={{ width: "auto" }} value={accountId} onChange={(e) => setAccountId(e.target.value)}>
          <option value="">Conta...</option>
          {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <input className="fw-file-hidden" id="ofx-file" type="file" accept=".ofx,.qfx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <label className="fw-btn ghost" htmlFor="ofx-file">Escolher arquivo</label>
        <span className="fw-file-name">{file ? file.name : "Nenhum .ofx selecionado"}</span>
        <Button type="submit">Enviar</Button>
      </form>
      {isLoading && <p>Carregando...</p>}
      <ul className="fw-list">
        {(data ?? []).map((i) => (
          <li className="fw-list-item" key={i.id}>
            <Button variant="link" onClick={() => navigate({ to: "/app/imports/$id", params: { id: String(i.id) } })}>
              #{i.id} {i.file_name}
            </Button>{" "}
            <Badge tone={verdictTone(i.status)}>{labelOf(importStatusLabel, i.status)}</Badge>
            <span>total {i.total_rows}, importados {i.imported_rows}, duplicados {i.duplicate_rows}</span>
            {i.error && <span className="fw-error"> — {i.error}</span>}
          </li>
        ))}
      </ul>
    </>
  );
}
