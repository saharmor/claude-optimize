import { useState } from "react";

interface Props {
  code: string;
  language?: string;
}

export default function CodeBlock({ code, language = "text" }: Props) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState("");
  const languageLabel = language.toUpperCase();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopyError("");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError("Clipboard access is unavailable in this browser.");
    }
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-block-toolbar">
        <span className="code-language">{languageLabel}</span>
        <button type="button" className="copy-btn" onClick={handleCopy}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      {copyError && <div className="hint">{copyError}</div>}
      <div className="code-block">
        <pre>{code}</pre>
      </div>
    </div>
  );
}
