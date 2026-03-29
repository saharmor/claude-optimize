import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  tone?: "neutral" | "accent" | "success" | "warning" | "danger" | "info";
  className?: string;
}

export default function Pill({
  children,
  tone = "neutral",
  className = "",
}: Props) {
  const classes = ["pill", `pill-${tone}`, className].filter(Boolean).join(" ");

  return <span className={classes}>{children}</span>;
}
