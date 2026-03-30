interface Props {
  count: number;
  onGeneratePrompt: () => void;
  onClear: () => void;
}

export default function SelectionBar({ count, onGeneratePrompt, onClear }: Props) {
  if (count === 0) return null;

  return (
    <div className="selection-bar">
      <span className="selection-bar-count">
        {count} finding{count !== 1 ? "s" : ""} selected
      </span>
      <div className="selection-bar-actions">
        <button type="button" className="selection-bar-clear" onClick={onClear}>
          Clear
        </button>
        <button
          type="button"
          className="selection-bar-generate"
          onClick={onGeneratePrompt}
        >
          Generate coding prompt
        </button>
      </div>
    </div>
  );
}
