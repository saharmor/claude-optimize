import { useState } from "react";
import type { AnalyzerType, Finding } from "../types/scan";
import { ANALYZER_LABELS, ANALYZER_ICONS } from "../types/scan";
import FindingCard from "./FindingCard";
import { Pill } from "./ui";

interface Props {
  analyzer: AnalyzerType;
  findings: Finding[];
}

export default function AnalyzerSection({ analyzer, findings }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="analyzer-section">
      <button
        type="button"
        className="analyzer-section-header"
        onClick={() => setOpen(!open)}
      >
        <div className="analyzer-section-left">
          <span className="analyzer-section-icon">{ANALYZER_ICONS[analyzer]}</span>
          <span className="analyzer-section-title">
            {ANALYZER_LABELS[analyzer]}
          </span>
          <Pill tone="neutral" className="finding-count">
            {findings.length} finding{findings.length !== 1 ? "s" : ""}
          </Pill>
        </div>
        <span className={`chevron ${open ? "open" : ""}`}>&#9660;</span>
      </button>

      {open && (
        <div className="analyzer-section-body">
          {findings.length === 0 ? (
            <p className="analyzer-empty-copy">
              No issues found. Your code looks good in this area.
            </p>
          ) : (
            findings.map((finding) => (
              <FindingCard
                key={`${finding.location.file}:${finding.location.lines}:${finding.recommendation.title}`}
                finding={finding}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
