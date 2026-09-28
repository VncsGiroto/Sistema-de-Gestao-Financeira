import { useEffect, useState } from "react";
import { useAuth } from "../../lib/auth-store";
import { api } from "../../lib/api";
import type { User } from "../../lib/api";
import { useAccounts } from "../finance/hooks";
import { CategoryPie, EvolutionChart } from "./charts";
import { useCommitments, useDashboard } from "./hooks";
import { brl } from "../../lib/money";

export function DashboardPage() {
  const { access, refresh } = useAuth();
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

  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [accountId, setAccountId] = useState("");
  const { data: dash } = useDashboard({
    from: from || undefined, to: to || undefined,
    account_id: accountId ? Number(accountId) : undefined,
  });
  const { data: accounts } = useAccounts();
  const [horizon, setHorizon] = useState(60);
  const { data: comm } = useCommitments(horizon);

  return (
    <>
      <div className="fw-page-head">
        <h1>Painel</h1>
        {user ? <p>Bem-vindo, {user.name}</p> : <p>Carregando sessão...</p>}
        {error && <p className="fw-error">{error}</p>}
      </div>
      <div className="fw-row">
        <input className="fw-input" style={{ width: "auto" }} type="date" value={from} onChange={(e) => setFrom(e.target.value)} aria-label="De" />
        <input className="fw-input" style={{ width: "auto" }} type="date" value={to} onChange={(e) => setTo(e.target.value)} aria-label="Até" />
        <select className="fw-select" style={{ width: "auto" }} value={accountId} onChange={(e) => setAccountId(e.target.value)} aria-label="Conta">
          <option value="">Todas as contas</option>
          {(accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
      </div>
      {dash && (
        <>
          <div className="fw-metrics">
            <div className="fw-metric"><strong>Saldo</strong><p>{brl(dash.balance)}</p></div>
            <div className="fw-metric"><strong>Receitas</strong><p>{brl(dash.income.total)}</p></div>
            <div className="fw-metric"><strong>Despesas</strong><p>{brl(dash.expense.total)}</p></div>
          </div>
          <div className="fw-card" style={{ marginBottom: 12 }}>
            <EvolutionChart data={dash} />
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <div className="fw-card" style={{ flex: 1, minWidth: 260 }}><CategoryPie title="Receitas por categoria" items={dash.income.by_category} /></div>
            <div className="fw-card" style={{ flex: 1, minWidth: 260 }}><CategoryPie title="Despesas por categoria" items={dash.expense.by_category} /></div>
          </div>
        </>
      )}
      <section className="fw-card" style={{ marginTop: 16 }}>
        <h2>Compromissos futuros (projeção)</h2>
        <p>Contas a vencer e parcelas dentro do horizonte. Não entram no realizado acima.</p>
        <select className="fw-select" style={{ width: "auto" }} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} aria-label="Horizonte">
          <option value={30}>Próximos 30 dias</option>
          <option value={60}>Próximos 60 dias</option>
          <option value={90}>Próximos 90 dias</option>
        </select>
        {comm && (
          <>
            <p>Total em compromissos: {brl(comm.total)} — Saldo projetado: {brl(String(Number(dash?.balance ?? 0) - Number(comm.total)))}</p>
            <ul className="fw-list">
              {comm.items.map((c, i) => (
                <li className="fw-list-item" key={`${c.kind}-${c.ref_id}-${i}`}>
                  {c.due_date} — {c.description} — {brl(c.amount)}
                  {" "}({c.kind === "bill" ? "Conta futura" : "Parcelamento"})
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}
