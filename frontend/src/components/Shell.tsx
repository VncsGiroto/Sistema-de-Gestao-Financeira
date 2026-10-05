import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useAuth } from "../lib/auth-store";

const SECTIONS: { title: string; items: { to: "/app" | "/app/accounts" | "/app/categories" | "/app/transactions" | "/app/imports" | "/app/payables" | "/app/investments"; label: string; icon: string }[] }[] = [
  {
    title: "Meu dinheiro",
    items: [
      { to: "/app", label: "Painel", icon: "◈" },
      { to: "/app/accounts", label: "Contas", icon: "🏦" },
      { to: "/app/transactions", label: "Movimentações", icon: "⇄" },
      { to: "/app/imports", label: "Importações", icon: "📥" },
    ],
  },
  {
    title: "Planejamento",
    items: [{ to: "/app/payables", label: "Contas a pagar", icon: "🗓" }],
  },
  {
    title: "Patrimônio",
    items: [{ to: "/app/investments", label: "Investimentos", icon: "📈" }],
  },
  {
    title: "Configurações",
    items: [{ to: "/app/categories", label: "Categorias", icon: "🏷" }],
  },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  async function onLogout() {
    await logout();
    navigate({ to: "/login" });
  }

  return (
    <div className="fw-shell">
      <aside className="fw-sidebar">
        <div className="fw-brand">
          <span className="fw-brand-mark">F</span>
          <span>
            <span className="fw-brand-name">FinanceWay</span>
            <br />
            <span className="fw-brand-sub">gestão financeira</span>
          </span>
        </div>
        <div className="fw-nav-label">Menu</div>
        {SECTIONS.map((s) => (
          <div key={s.title}>
            <div className="fw-nav-label">{s.title}</div>
            {s.items.map((it) => {
              const active = it.to === "/app" ? pathname === "/app" : pathname.startsWith(it.to);
              return (
                <Link key={it.to} to={it.to} className={`fw-nav-item${active ? " active" : ""}`}>
                  <span className="fw-nav-icon">{it.icon}</span> {it.label}
                </Link>
              );
            })}
          </div>
        ))}
        <div className="fw-nav-foot">
          <button className="fw-nav-item" onClick={() => navigate({ to: "/app/security" })}>
            <span className="fw-nav-icon">🔒</span> Trocar senha
          </button>
          <button className="fw-nav-item" onClick={onLogout}>
            <span className="fw-nav-icon">↩</span> Sair
          </button>
        </div>
      </aside>
      <div className="fw-main">
        <header className="fw-topbar">{user ? `${user.name} · ${user.email}` : ""}</header>
        <div className="fw-content">{children}</div>
      </div>
    </div>
  );
}
