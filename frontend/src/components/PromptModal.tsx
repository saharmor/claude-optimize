import { useState, useEffect, useRef } from "react";

interface Props {
  promptText: string;
  onClose: () => void;
}

export default function PromptModal({ promptText, onClose }: Props) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState("");
  const copyTimerRef = useRef<ReturnType<typeof setTimeout>>();

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

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(promptText);
      setCopyError("");
      setCopied(true);
      copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError("Clipboard access is unavailable in this browser.");
    }
  };

  return (
    <div className="prompt-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="prompt-modal-title">
      <div className="prompt-modal" onClick={(e) => e.stopPropagation()}>
        <div className="prompt-modal-header">
          <h3 id="prompt-modal-title" className="prompt-modal-title">Handoff prompt</h3>
          <button
            type="button"
            className="prompt-modal-close"
            onClick={onClose}
          >
            &times;
          </button>
        </div>
        <p className="prompt-modal-hint">
          Copy this prompt and paste it into your coding agent (Claude Code, Cursor, etc.) to apply the selected fixes.
        </p>
        <pre className="prompt-modal-content">{promptText}</pre>
        <div className="prompt-modal-footer">
          <button
            type="button"
            className="prompt-modal-copy"
            onClick={handleCopy}
          >
            {copied ? "Copied!" : "Copy to clipboard"}
          </button>
          {copyError && <span className="hint">{copyError}</span>}
        </div>
      </div>
    </div>
  );
}
