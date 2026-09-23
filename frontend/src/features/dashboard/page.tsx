import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "../../lib/auth-store";
import { api } from "../../lib/api-client";
import type { User } from "../../lib/api-client";

export function DashboardPage() {
  const { access, logout, refresh } = useAuth();
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      if (!access) return;
      try {
        const { data } = await api.authFetch<User>("/auth/me", access, refresh);
        if (alive) setUser(data);
      } catch {
        if (alive) setError("Sessão expirada. Entre de novo.");
      }
    })();
    return () => {
      alive = false;
    };
  }, [access, refresh]);

  async function onLogout() {
    await logout();
    navigate({ to: "/login" });
  }

  return (
    <main style={{ fontFamily: "system-ui", padding: 32 }}>
      <h1>Painel</h1>
      {user ? <p>Bem-vindo, {user.name} ({user.email})</p> : <p>Carregando sessão...</p>}
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <p>
        <button onClick={onLogout}>Sair</button>{" "}
        <button onClick={() => navigate({ to: "/app/security" })}>Trocar senha</button>
      </p>
      <nav style={{ display: "flex", gap: 12 }}>
        <button onClick={() => navigate({ to: "/app/accounts" })}>Contas</button>
        <button onClick={() => navigate({ to: "/app/categories" })}>Categorias</button>
        <button onClick={() => navigate({ to: "/app/transactions" })}>Movimentações</button>
        <button onClick={() => navigate({ to: "/app/imports" })}>Importações</button>
      </nav>
    </main>
  );
}
