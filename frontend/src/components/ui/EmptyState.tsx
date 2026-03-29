import type { ReactNode } from "react";

interface Props {
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}

export default function EmptyState({
  title,
  description,
  action,
  className = "",
}: Props) {
  return (
    <div className={["empty-state", "surface", className].filter(Boolean).join(" ")}>
      <h3>{title}</h3>
      <p>{description}</p>
      {action ? <div className="empty-state-action">{action}</div> : null}
    </div>
  );
}
