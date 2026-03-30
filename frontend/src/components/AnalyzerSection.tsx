import { useState, useEffect } from "react";
import type { AnalyzerType, Finding } from "../types/scan";
import { ANALYZER_LABELS } from "../types/scan";
import { getFindingKey } from "../utils/findingKey";
import FindingCard from "./FindingCard";
import { Pill } from "./ui";

interface Props {
  analyzer: AnalyzerType;
  findings: Finding[];
  projectPath: string;
  focusKey?: string | null;
  selectedKeys?: Set<string>;
  onToggleFinding?: (key: string) => void;
}

export default function AnalyzerSection({ analyzer, findings, projectPath, focusKey, selectedKeys, onToggleFinding }: Props) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (focusKey && focusKey.startsWith(`${analyzer}:`)) {
      setOpen(true);
    }
  }, [focusKey, analyzer]);

  const isEmpty = findings.length === 0;

  if (isEmpty) {
    return (
      <div className="analyzer-section analyzer-section-clean">
        <div className="analyzer-section-header analyzer-section-header-static">
          <div className="analyzer-section-left">
            <span className="analyzer-section-title">
              {ANALYZER_LABELS[analyzer]}
            </span>
            <Pill tone="neutral" className="finding-count">
              No issues found
            </Pill>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="analyzer-section">
      <button
        type="button"
        className="analyzer-section-header"
        onClick={() => setOpen(!open)}
      >
        <div className="analyzer-section-left">
          <span className="analyzer-section-title">
            {ANALYZER_LABELS[analyzer]}
          </span>
          <Pill tone="neutral" className="finding-count">
            {findings.length} finding{findings.length !== 1 ? "s" : ""}
          </Pill>
        </div>
        <span className={`chevron ${open ? "open" : ""}`} />
      </button>

      {open && (
        <div className="analyzer-section-body">
          {findings.map((finding, index) => {
            const key = getFindingKey(finding);
            return (
              <FindingCard
                key={key}
                finding={finding}
                projectPath={projectPath}
                focusKey={focusKey}
                isSelected={selectedKeys?.has(key)}
                onToggle={onToggleFinding ? () => onToggleFinding(key) : undefined}

              />
            );
          })}
        </div>
      )}
    </div>
  );
}
