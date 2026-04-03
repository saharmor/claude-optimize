interface Props {
  count: number;
  onGeneratePrompt: () => void;
  onApply: () => void;
  onClear: () => void;
}

export default function SelectionBar({ count, onGeneratePrompt, onApply, onClear }: Props) {
  return (
    <div className={`selection-bar ${count > 0 ? "selection-bar-visible" : ""}`}>
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
        <button
          type="button"
          className="selection-bar-apply"
          onClick={onApply}
        >
          Apply
          <span aria-hidden="true" style={{ marginLeft: 6 }}>&rarr;</span>
        </button>
      </div>
    </div>
  );
}
