import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useAuth } from "../../lib/auth-store";
import { ApiError, api } from "../../lib/api-client";

const box: React.CSSProperties = { maxWidth: 400, margin: "64px auto", fontFamily: "system-ui", padding: 16 };
const input: React.CSSProperties = { width: "100%", padding: 10, margin: "8px 0", boxSizing: "border-box" };
const btn: React.CSSProperties = { width: "100%", padding: 12, marginTop: 8, cursor: "pointer" };

function message(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401) return "E-mail ou senha inválidos.";
    return e.message;
  }
  return "Falha inesperada. Tente de novo.";
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    setError("");
    if (!email.includes("@")) return setError("Informe um e-mail válido.");
    if (!password) return setError("Informe a senha.");
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigate({ to: "/app" });
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={box}>
      <h1>Entrar</h1>
      <form onSubmit={onSubmit}>
        <input style={input} placeholder="E-mail" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        <input style={input} type="password" placeholder="Senha" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        {error && <p style={{ color: "crimson" }}>{error}</p>}
        <button style={btn} disabled={busy}>{busy ? "Entrando..." : "Entrar"}</button>
      </form>
      <p><Link to="/register">Criar conta</Link> · <Link to="/recover">Esqueci a senha</Link></p>
    </main>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    setError("");
    if (name.trim().length < 2) return setError("Informe seu nome.");
    if (!email.includes("@")) return setError("Informe um e-mail válido.");
    if (password.length < 8) return setError("Senha mínima de 8 caracteres.");
    setBusy(true);
    try {
      await register(name.trim(), email.trim(), password);
      navigate({ to: "/app" });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setError("E-mail já cadastrado. Tente entrar.");
      else setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={box}>
      <h1>Criar conta</h1>
      <form onSubmit={onSubmit}>
        <input style={input} placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
        <input style={input} placeholder="E-mail" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        <input style={input} type="password" placeholder="Senha (mín. 8)" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        {error && <p style={{ color: "crimson" }}>{error}</p>}
        <button style={btn} disabled={busy}>{busy ? "Criando..." : "Criar conta"}</button>
      </form>
      <p><Link to="/login">Já tenho conta</Link></p>
    </main>
  );
}

export function RecoverPage() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    if (!email.includes("@")) return setDone("Informe um e-mail válido.");
    setBusy(true);
    try {
      const res = await api.recover(email.trim());
      setDone(res.message);
    } catch (e) {
      setDone(message(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={box}>
      <h1>Recuperar senha</h1>
      <form onSubmit={onSubmit}>
        <input style={input} placeholder="E-mail" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        {done && <p>{done}</p>}
        <button style={btn} disabled={busy}>{busy ? "Enviando..." : "Enviar instruções"}</button>
      </form>
      <p><Link to="/login">Voltar ao login</Link></p>
    </main>
  );
}

export function ResetPage() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    if (token.length < 10) return setDone("Token inválido.");
    if (password.length < 8) return setDone("Senha mínima de 8 caracteres.");
    setBusy(true);
    try {
      await api.reset(token.trim(), password);
      setDone("Senha redefinida. Volte ao login.");
    } catch (e) {
      setDone(message(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={box}>
      <h1>Redefinir senha</h1>
      <form onSubmit={onSubmit}>
        <input style={input} placeholder="Token recebido" value={token} onChange={(e) => setToken(e.target.value)} />
        <input style={input} type="password" placeholder="Nova senha (mín. 8)" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        {done && <p>{done}</p>}
        <button style={btn} disabled={busy}>{busy ? "Salvando..." : "Redefinir"}</button>
      </form>
      <p><Link to="/login">Voltar ao login</Link></p>
    </main>
  );
}
