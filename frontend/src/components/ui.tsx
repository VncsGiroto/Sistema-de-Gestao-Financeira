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
