import { useState } from "react";
import { Highlight, themes } from "prism-react-renderer";

interface Props {
  code: string;
  language?: string;
}

function normalizeLanguage(lang?: string): string {
  if (!lang) return "python";
  const l = lang.toLowerCase().trim();
  const map: Record<string, string> = {
    py: "python",
    python: "python",
    js: "javascript",
    javascript: "javascript",
    ts: "typescript",
    typescript: "typescript",
    md: "markdown",
    markdown: "markdown",
    json: "json",
    bash: "bash",
    sh: "bash",
    shell: "bash",
    yaml: "yaml",
    yml: "yaml",
    jsx: "jsx",
    tsx: "tsx",
  };
  return map[l] || l;
}

export default function CodeBlock({ code, language }: Props) {
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

  const lang = normalizeLanguage(language);

  return (
    <div className="code-block">
      <button type="button" className="copy-btn" onClick={handleCopy}>
        {copied ? "Copied!" : "Copy"}
      </button>
      {copyError && <div className="hint">{copyError}</div>}
      <Highlight theme={themes.github} code={code.trim()} language={lang}>
        {({ style, tokens, getLineProps, getTokenProps }) => (
          <pre style={{ ...style, margin: 0, background: "transparent", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line })}>
                {line.map((token, key) => (
                  <span key={key} {...getTokenProps({ token })} />
                ))}
              </div>
            ))}
          </pre>
        )}
      </Highlight>
    </div>
  );
}
