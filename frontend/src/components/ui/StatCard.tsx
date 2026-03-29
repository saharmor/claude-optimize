import type { ReactNode } from "react";

interface Props {
  value: ReactNode;
  label: ReactNode;
  className?: string;
  valueClassName?: string;
}

export default function StatCard({
  value,
  label,
  className = "",
  valueClassName = "",
}: Props) {
  return (
    <div className={["stat-card", className].filter(Boolean).join(" ")}>
      <div className={["stat-card-value", valueClassName].filter(Boolean).join(" ")}>
        {value}
      </div>
      <div className="stat-card-label">{label}</div>
    </div>
  );
}
