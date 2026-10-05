import { useEffect, useState } from "react";
import { useAuth } from "../../lib/auth-store";
import { api } from "../../lib/api";
import type { User } from "../../lib/api";
import { Link } from "@tanstack/react-router";
import { useAccounts } from "../finance/hooks";
import { Badge } from "../../components/ui";
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
  const { data: comm } = useCommitments(horizon, accountId ? Number(accountId) : undefined);

  const prev = dash?.prev_month;
  const varFmt = (cur: string | undefined, old: string | undefined) => {
    if (cur == null || old == null) return "—";
    const d = Number(cur) - Number(old);
    if (Number(old) === 0) return d === 0 ? "—" : `${d > 0 ? "+" : ""}${d.toFixed(2)} (sem base anterior)`;
    return `${d > 0 ? "+" : ""}${((d / Math.abs(Number(old))) * 100).toFixed(1)}% vs ${prev?.month}`;
  };

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
      {accounts && accounts.length === 0 && (
        <div className="fw-card" style={{ marginTop: 12 }}>
          <h2 style={{ marginTop: 0 }}>Comece por aqui</h2>
          <ol>
            <li><Link to="/app/accounts">Crie sua primeira conta</Link></li>
            <li><Link to="/app/transactions">Lance uma movimentação</Link> ou <Link to="/app/imports">importe seu extrato OFX</Link></li>
            <li><Link to="/app/categories">Organize as categorias</Link></li>
            <li><Link to="/app/payables">Cadastre uma conta futura</Link></li>
          </ol>
        </div>
      )}
      {dash && (
        <>
          <div className="fw-metrics">
            <div className="fw-metric"><strong>Saldo</strong><p>{brl(dash.balance)}</p></div>
            <div className="fw-metric"><strong>Receitas</strong><p>{brl(dash.income.total)}</p><small>{varFmt(dash.income.total, prev?.income)}</small></div>
            <div className="fw-metric"><strong>Despesas</strong><p>{brl(dash.expense.total)}</p><small>{varFmt(dash.expense.total, prev?.expense)}</small></div>
          </div>
          {(dash.uncategorized > 0) && (
            <p>{dash.uncategorized} lançamento(s) sem categoria no período — categorize no extrato.</p>
          )}
          {(accounts ?? []).length > 0 && (
            <div className="fw-card" style={{ marginBottom: 12 }}>
              <h2 style={{ marginTop: 0 }}>Contas</h2>
              <ul className="fw-list">
                {(accounts ?? []).map((a) => (
                  <li className="fw-list-item" key={a.id}>
                    <span>{a.name} — Atual {brl(a.current_balance)}</span>
                    {Number(a.current_balance) < 0 && <Badge tone="red">saldo negativo</Badge>}
                  </li>
                ))}
              </ul>
            </div>
          )}
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
        <p>Saldo projetado = saldo atual − compromissos dentro do horizonte. Não entram no realizado acima.</p>
        <select className="fw-select" style={{ width: "auto" }} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} aria-label="Horizonte">
          <option value={30}>Próximos 30 dias</option>
          <option value={60}>Próximos 60 dias</option>
          <option value={90}>Próximos 90 dias</option>
        </select>
        {comm && (
          <>
            <p>Total em compromissos: {brl(comm.total)} — Saldo projetado: {brl(String(Number(dash?.balance ?? 0) - Number(comm.total)))}</p>
            {Number(comm.unassigned_total) > 0 && (
              <p>Projeção parcial: {brl(comm.unassigned_total)} em compromissos sem conta definida ficaram de fora.</p>
            )}
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
