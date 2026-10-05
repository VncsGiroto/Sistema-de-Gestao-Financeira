interface LogoProps {
  variant?: "full" | "mark";
  size?: number;
}

/** Marca FinanceWay. `full` = símbolo + nome; `mark` = só o símbolo. */
export function Logo({ variant = "full", size = 32 }: LogoProps) {
  if (variant === "mark") {
    return <img src="/logo-mark.svg" alt="FinanceWay" width={size} height={size} />;
  }
  return <img src="/logo.svg" alt="FinanceWay" height={size} />;
}
