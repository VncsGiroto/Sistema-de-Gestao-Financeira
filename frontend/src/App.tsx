import { useEffect, useState } from "react";
import { getHealth } from "./lib/api-client";

export default function App() {
  const [status, setStatus] = useState("carregando...");
  useEffect(() => {
    getHealth()
      .then((h) => setStatus(`${h.status} — ${h.app}`))
      .catch((e) => setStatus(`API indisponível: ${e.message}`));
  }, []);
  return (
    <main style={{ fontFamily: "system-ui", padding: 32 }}>
      <h1>FinanceWay — Etapa 1 Docker</h1>
      <p>API health: {status}</p>
      <p>Swagger: /api/docs</p>
    </main>
  );
}
