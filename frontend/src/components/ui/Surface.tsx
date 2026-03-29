import type { HTMLAttributes, ReactNode } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  tone?: "default" | "muted";
  className?: string;
}

export default function Surface({
  children,
  tone = "default",
  className = "",
  ...props
}: Props) {
  const classes = [
    "surface",
    tone === "muted" ? "surface-muted" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div {...props} className={classes}>
      {children}
    </div>
  );
}
