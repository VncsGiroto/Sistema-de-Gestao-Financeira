import { useState } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { BackButton } from "./BackButton";

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger" | "link";
  size?: "md" | "sm";
};

export function Button({ variant = "primary", size = "md", className = "", ...rest }: BtnProps) {
  const cls = `fw-btn${variant === "ghost" ? " ghost" : ""}${variant === "danger" ? " danger" : ""}${
    variant === "link" ? " linklike" : ""
  }${size === "sm" ? " sm" : ""} ${className}`.trim();
  return <button className={cls} {...rest} />;
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`fw-card ${className}`.trim()}>{children}</div>;
}

export function PageHeader({ title, sub, backTo }: { title: string; sub?: string; backTo?: "/app" | "/app/imports" }) {
  return (
    <div className="fw-page-head">
      <h1>{title}</h1>
      {sub && <p>{sub}</p>}
      <BackButton to={backTo} />
    </div>
  );
}

export function Badge({ tone = "", children }: { tone?: "" | "green" | "red" | "amber" | "blue"; children: ReactNode }) {
  return <span className={`fw-badge ${tone}`.trim()}>{children}</span>;
}

export function verdictTone(v: string): "" | "green" | "red" | "amber" | "blue" {
  if (v === "NEW" || v === "IMPORTED" || v === "VALIDATED") return "green";
  if (v === "EXACT_DUPLICATE" || v === "FAILED") return "red";
  if (v === "FUZZY_CANDIDATE" || v === "PROCESSING" || v === "RECEIVED") return "amber";
  return "blue";
}

export interface ConfirmAsk {
  title: string;
  body: string;
  confirmLabel?: string;
}

/** Confirmação contextual com impacto explícito. Uso:
 *  const confirm = useConfirm();
 *  {confirm.dialog}
 *  onClick={async () => { if (await confirm.ask({title, body})) doIt(); }}
 */
export function useConfirm() {
  const [ask, setAsk] = useState<(ConfirmAsk & { resolve: (ok: boolean) => void }) | null>(null);
  return {
    dialog: ask ? (
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={ask.title}
        style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
        onClick={() => { ask.resolve(false); setAsk(null); }}
      >
        <div className="fw-card" style={{ maxWidth: 440 }} onClick={(e) => e.stopPropagation()}>
          <h2 style={{ marginTop: 0 }}>{ask.title}</h2>
          <p>{ask.body}</p>
          <div className="fw-row" style={{ justifyContent: "flex-end" }}>
            <Button variant="ghost" onClick={() => { ask.resolve(false); setAsk(null); }}>Cancelar</Button>
            <Button variant="danger" onClick={() => { ask.resolve(true); setAsk(null); }}>
              {ask.confirmLabel ?? "Confirmar"}
            </Button>
          </div>
        </div>
      </div>
    ) : null,
    ask: (a: ConfirmAsk) => new Promise<boolean>((resolve) => setAsk({ ...a, resolve })),
  };
}
