import { useNavigate } from "@tanstack/react-router";

/** Volta sempre para o destino padrão (Painel; review volta para a lista). */
export function BackButton({ to = "/app" }: { to?: "/app" | "/app/imports" }) {
  const navigate = useNavigate();
  return <button className="fw-btn ghost sm" onClick={() => navigate({ to })}>← Voltar</button>;
}
