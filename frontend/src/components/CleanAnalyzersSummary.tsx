import { useState } from "react";
import type { AnalyzerType } from "../types/scan";
import { ANALYZER_LABELS } from "../types/scan";
import { Pill } from "./ui";

interface Props {
  analyzers: AnalyzerType[];
}

export default function CleanAnalyzersSummary({ analyzers }: Props) {
  const [open, setOpen] = useState(false);

  if (analyzers.length === 0) return null;

  return (
    <div className="analyzer-section">
      <button
        type="button"
        className="analyzer-section-header"
        onClick={() => setOpen(!open)}
      >
        <div className="analyzer-section-left">
          <span className="analyzer-section-title">
            {analyzers.length} analyzer{analyzers.length !== 1 ? "s" : ""} found
            no issues
          </span>
          <Pill tone="success" className="finding-count">
            &#10003; All clear
          </Pill>
        </div>
        <span className={`chevron ${open ? "open" : ""}`} />
      </button>

      {open && (
        <div className="analyzer-section-body">
          <div className="clean-analyzer-chips">
            {analyzers.map((a) => (
              <span key={a} className="clean-analyzer-chip">
                {ANALYZER_LABELS[a]}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
