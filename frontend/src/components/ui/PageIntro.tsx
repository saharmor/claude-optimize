import type { ReactNode } from "react";

interface Props {
  eyebrow: string;
  title: string;
  description: string;
  size?: "page" | "section" | "subsection";
  className?: string;
  children?: ReactNode;
}

export default function PageIntro({
  eyebrow,
  title,
  description,
  size = "page",
  className = "",
  children,
}: Props) {
  const wrapperClassName = ["page-header-block", className].filter(Boolean).join(" ");
  const titleClassName =
    size === "page"
      ? "page-title"
      : size === "section"
        ? "section-title"
        : "section-subtitle";
  const copyClassName = size === "page" ? "page-lede" : "section-copy";
  const TitleTag = size === "page" ? "h1" : size === "section" ? "h1" : "h2";

  return (
    <div className={wrapperClassName}>
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <TitleTag className={titleClassName}>{title}</TitleTag>
      <p className={copyClassName}>{description}</p>
      {children}
    </div>
  );
}
