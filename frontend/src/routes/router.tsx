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
import { DashboardPage } from "../features/dashboard/page";
import { SecurityPage } from "../features/dashboard/security";
import { LoginPage, RecoverPage, RegisterPage, ResetPage } from "../features/auth/pages";

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
  return <>{children}</>;
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

const routeTree = rootRoute.addChildren([indexRoute, loginRoute, registerRoute, recoverRoute, resetRoute, appRoute, securityRoute]);
const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function AppRouter() {
  return <RouterProvider router={router} />;
}
