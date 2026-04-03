import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Highlight, themes } from "prism-react-renderer";

interface Props {
  content: string;
}

function normalizeLanguage(lang?: string): string {
  if (!lang) return "bash";
  const l = lang.toLowerCase().trim();
  const map: Record<string, string> = {
    py: "python",
    python: "python",
    js: "javascript",
    javascript: "javascript",
    ts: "typescript",
    typescript: "typescript",
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="copy-btn"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        } catch { /* clipboard access denied */ }
      }}
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

export default function MarkdownContent({ content }: Props) {
  const [copied, setCopied] = useState(false);

  // Return null for empty content, including content that's just empty code fences
  if (!content || !content.replace(/```\w*/g, "").trim()) return null;

  return (
    <div className="markdown-content">
      <button
        type="button"
        className="copy-btn"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          } catch { /* clipboard access denied */ }
        }}
      >
        {copied ? "Copied!" : "Copy"}
      </button>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const codeString = String(children).replace(/\n$/, "");

            if (!match) {
              return (
                <code className="md-inline-code" {...props}>
                  {children}
                </code>
              );
            }

            const lang = normalizeLanguage(match[1]);

            return (
              <div className="code-block md-code-block">
                <CopyButton text={codeString} />
                <Highlight
                  theme={themes.github}
                  code={codeString}
                  language={lang}
                >
                  {({ style, tokens, getLineProps, getTokenProps }) => (
                    <pre
                      style={{
                        ...style,
                        margin: 0,
                        background: "transparent",
                        whiteSpace: "pre-wrap",
                        overflowWrap: "anywhere",
                      }}
                    >
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
          },
        }}
      />
    </div>
  );
}
