import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "../../lib/auth-store";
import { ApiError, api } from "../../lib/api-client";
import { Button, PageHeader } from "../../components/ui";

export function SecurityPage() {
  const { access, logout } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    if (next.length < 8) return setMsg("Nova senha mínima de 8 caracteres.");
    if (!access) return setMsg("Sem sessão.");
    setBusy(true);
    try {
      await api.change(current, next, access);
      setMsg("Senha trocada. Entre de novo.");
      await logout();
      navigate({ to: "/login" });
    } catch (e) {
      setMsg(e instanceof ApiError && e.status === 401 ? "Senha atual incorreta." : "Falha. Tente de novo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Trocar senha" sub="Sua sessão será encerrada após a troca." />
      <form onSubmit={onSubmit} className="fw-card" style={{ maxWidth: 400 }}>
        <input
          className="fw-input"
          style={{ margin: "8px 0" }}
          type="password"
          placeholder="Senha atual"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          autoComplete="current-password"
        />
        <input
          className="fw-input"
          style={{ margin: "8px 0" }}
          type="password"
          placeholder="Nova senha (mín. 8)"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          autoComplete="new-password"
        />
        {msg && <p>{msg}</p>}
        <Button style={{ width: "100%" }} disabled={busy}>
          {busy ? "Salvando..." : "Trocar senha"}
        </Button>
      </form>
    </>
  );
}
