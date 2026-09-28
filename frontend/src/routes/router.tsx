import { useEffect, useRef } from "react";
import {
  Outlet,
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
  useNavigate,
} from "@tanstack/react-router";
import { useAuth } from "../lib/auth-store";
import { Shell } from "../components/Shell";
import { DashboardPage } from "../features/dashboard/page";
import { SecurityPage } from "../features/dashboard/security";
import { LoginPage, RecoverPage, RegisterPage, ResetPage } from "../features/auth/pages";
import { AccountsPage } from "../features/finance/accounts";
import { CategoriesPage } from "../features/finance/categories";
import { TransactionsPage } from "../features/finance/transactions";
import { ImportsPage } from "../features/imports/list";
import { ReviewPage } from "../features/imports/review";
import { PayablesPage } from "../features/payables/page";

function Guard({ children }: { children: React.ReactNode }) {
  const { access, ready, refresh } = useAuth();
  const navigate = useNavigate();
  const tried = useRef(false);

  useEffect(() => {
    // reload direto em /app*: access em memória se perdeu → tenta restaurar via refresh
    if (!access && !tried.current) {
      tried.current = true;
      refresh().catch(() => navigate({ to: "/login" }));
    }
  }, [access, refresh, navigate]);

  if (!ready) return <p style={{ padding: 32 }}>Carregando...</p>;
  if (!access) return <p style={{ padding: 32 }}>Redirecionando para login...</p>;
  return <Shell>{children}</Shell>;
}

const rootRoute = createRootRoute({ component: () => <Outlet /> });
const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: "/login", component: LoginPage });
const registerRoute = createRoute({ getParentRoute: () => rootRoute, path: "/register", component: RegisterPage });
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app",
  component: () => (
    <Guard>
      <DashboardPage />
    </Guard>
  ),
});
const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: "/", component: LoginPage });
const recoverRoute = createRoute({ getParentRoute: () => rootRoute, path: "/recover", component: RecoverPage });
const resetRoute = createRoute({ getParentRoute: () => rootRoute, path: "/reset", component: ResetPage });
const securityRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/security",
  component: () => (
    <Guard>
      <SecurityPage />
    </Guard>
  ),
});
const accountsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/accounts",
  component: () => (
    <Guard>
      <AccountsPage />
    </Guard>
  ),
});
const categoriesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/categories",
  component: () => (
    <Guard>
      <CategoriesPage />
    </Guard>
  ),
});
const transactionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/transactions",
  component: () => (
    <Guard>
      <TransactionsPage />
    </Guard>
  ),
});
const importsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/imports",
  component: () => (
    <Guard>
      <ImportsPage />
    </Guard>
  ),
});
const reviewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/imports/$id",
  component: function ReviewRoute() {
    const { id } = reviewRoute.useParams();
    return (
      <Guard>
        <ReviewPage id={Number(id)} />
      </Guard>
    );
  },
});
const payablesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/payables",
  component: () => (
    <Guard>
      <PayablesPage />
    </Guard>
  ),
});

const routeTree = rootRoute.addChildren([indexRoute, loginRoute, registerRoute, recoverRoute, resetRoute, appRoute, securityRoute, accountsRoute, categoriesRoute, transactionsRoute, importsRoute, reviewRoute, payablesRoute]);
const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function AppRouter() {
  return <RouterProvider router={router} />;
}
