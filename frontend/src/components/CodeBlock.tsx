import { useState } from "react";

interface Props {
  code: string;
  language?: string;
}

export default function CodeBlock({ code }: Props) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState("");
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
    <div className="code-block">
      <button type="button" className="copy-btn" onClick={handleCopy}>
        {copied ? "Copied!" : "Copy"}
      </button>
      {copyError && <div className="hint">{copyError}</div>}
      <pre>{code}</pre>
    </div>
  );
}
