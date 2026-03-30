import { useEffect, useRef, useState } from "react";
import type { ScanResult } from "../types/scan";

interface Props {
  scan: ScanResult;
  projectName: string;
  onClose: () => void;
}

function generateSocialPost(scan: ScanResult, projectName: string): string {
  const { scorecard } = scan;
  if (!scorecard) return "";

  const oneLiner = scan.project_summary?.one_liner;
  const projectDesc = oneLiner
    ? `${projectName} (${oneLiner.replace(/\.$/, "")})`
    : projectName;

  const lines: string[] = [];

  lines.push(`Ran Claude Optimize on ${projectDesc} and it found ${scorecard.total_findings} thing${scorecard.total_findings !== 1 ? "s" : ""} we could improve in how we call LLM APIs.`);

  if (scorecard.top_wins.length > 0) {
    lines.push("");
    lines.push("Some highlights:");
    for (const win of scorecard.top_wins.slice(0, 3)) {
      lines.push(`- ${win.title} (${win.estimated_savings})`);
    }
  }

  if (scorecard.estimated_total_savings) {
    lines.push("");
    lines.push(`Total estimated impact: ${scorecard.estimated_total_savings}`);
  }

  lines.push("");
  lines.push("It scans your codebase for prompt caching opportunities, batching, model selection, and more. Takes a couple minutes to set up. Pretty useful if you're spending real money on API calls.");
  lines.push("");
  lines.push("https://github.com/saharmor/claude-optimize");

  return lines.join("\n");
}

function generateSlackMessage(scan: ScanResult, projectName: string): string {
  const { scorecard } = scan;
  if (!scorecard) return "";

  const oneLiner = scan.project_summary?.one_liner;
  const projectDesc = oneLiner
    ? `${projectName} (${oneLiner.replace(/\.$/, "")})`
    : projectName;

  const lines: string[] = [];
  lines.push(`Hey All, ran *Claude Optimize* on ${projectDesc} and it found *${scorecard.total_findings} optimization${scorecard.total_findings !== 1 ? "s" : ""}* we should look at.`);

  if (scorecard.top_wins.length > 0) {
    lines.push("");
    for (const win of scorecard.top_wins.slice(0, 3)) {
      lines.push(`• ${win.title} (${win.estimated_savings})`);
    }
  }

  if (scorecard.estimated_total_savings) {
    lines.push("");
    lines.push(`Estimated impact: *${scorecard.estimated_total_savings}*`);
  }

  lines.push("");
  lines.push("Worth running on your projects too: https://github.com/saharmor/claude-optimize");

  return lines.join("\n");
}

type ShareTab = "social" | "slack";

const TAB_LABELS: Record<ShareTab, string> = {
  social: "Post",
  slack: "Slack",
};

const TAB_DESCRIPTIONS: Record<ShareTab, string> = {
  social: "Share on X, forums, or with your community",
  slack: "Formatted for Slack with bold markdown",
};

export default function ShareModal({ scan, projectName, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<ShareTab>("social");
  const [copied, setCopied] = useState(false);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
    };
  }, [onClose]);

  const texts: Record<ShareTab, string> = {
    social: generateSocialPost(scan, projectName),
    slack: generateSlackMessage(scan, projectName),
  };

  const activeText = texts[activeTab];

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(activeText);
      setCopied(true);
      copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = activeText;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="share-modal-backdrop" onClick={onClose}>
      <div className="share-modal" onClick={(e) => e.stopPropagation()}>
        <div className="share-modal-header">
          <h2 className="share-modal-title">Share Results</h2>
          <button
            type="button"
            className="share-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        <div className="share-tabs">
          {(["social", "slack"] as ShareTab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              className={`share-tab ${activeTab === tab ? "share-tab-active" : ""}`}
              onClick={() => {
                setActiveTab(tab);
                setCopied(false);
              }}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        <p className="share-tab-description">{TAB_DESCRIPTIONS[activeTab]}</p>

        <div className="share-preview">
          <pre className="share-preview-text">{activeText}</pre>
        </div>

        <div className="share-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Done
          </button>
          <button type="button" className="btn btn-primary share-copy-btn" onClick={handleCopy}>
            {copied ? "Copied!" : "Copy to Clipboard"}
          </button>
        </div>
      </div>
    </div>
  );
}
