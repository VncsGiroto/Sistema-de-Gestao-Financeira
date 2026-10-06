import { forwardRef, useEffect, useRef, useState } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { BackButton } from "./BackButton";

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger" | "link";
  size?: "md" | "sm";
};

export const Button = forwardRef<HTMLButtonElement, BtnProps>(function Button(
  { variant = "primary", size = "md", className = "", ...rest },
  ref,
) {
  const cls = `fw-btn${variant === "ghost" ? " ghost" : ""}${variant === "danger" ? " danger" : ""}${
    variant === "link" ? " linklike" : ""
  }${size === "sm" ? " sm" : ""} ${className}`.trim();
  return <button ref={ref} className={cls} {...rest} />;
});

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

/** Rótulo persistente acima do campo (placeholder sozinho não basta). */
export function Field({ label, hint, title, children }: { label: string; hint?: string; title?: string; children: ReactNode }) {
  return (
    <label className="fw-field">
      <span title={title}>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
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
  const confirmRef = useRef<HTMLButtonElement | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const prevFocus = useRef<Element | null>(null);
  useEffect(() => {
    if (!ask) return;
    prevFocus.current = document.activeElement;
    confirmRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        ask.resolve(false);
        setAsk(null);
        return;
      }
      // Mantém o foco preso dentro do modal enquanto aberto.
      if (e.key === "Tab") {
        const root = rootRef.current;
        if (!root) return;
        const items = Array.from(
          root.querySelectorAll<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])"),
        ).filter((el) => !el.hasAttribute("disabled"));
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (prevFocus.current instanceof HTMLElement) prevFocus.current.focus();
    };
  }, [ask]);
  return {
    dialog: ask ? (
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={ask.title}
        style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
        onClick={() => { ask.resolve(false); setAsk(null); }}
      >
        <div ref={rootRef} className="fw-card" style={{ maxWidth: 440 }} onClick={(e) => e.stopPropagation()}>
          <h2 style={{ marginTop: 0 }}>{ask.title}</h2>
          <p>{ask.body}</p>
          <div className="fw-row" style={{ justifyContent: "flex-end" }}>
            <Button variant="ghost" onClick={() => { ask.resolve(false); setAsk(null); }}>Cancelar</Button>
            <Button variant="danger" ref={confirmRef} onClick={() => { ask.resolve(true); setAsk(null); }}>
              {ask.confirmLabel ?? "Confirmar"}
            </Button>
          </div>
        </div>
      </div>
    ) : null,
    ask: (a: ConfirmAsk) => new Promise<boolean>((resolve) => setAsk({ ...a, resolve })),
  };
}
