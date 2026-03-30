import { useEffect } from "react";

interface Props {
  findingCount: number;
  onRun: () => void;
  onCancel: () => void;
}

export default function ApplyConfirmModal({ findingCount, onRun, onCancel }: Props) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  return (
    <div
      className="apply-confirm-backdrop"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="apply-confirm-title"
    >
      <div className="apply-confirm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="apply-confirm-header">
          <h3 id="apply-confirm-title" className="apply-confirm-title">
            Apply with Claude Code
          </h3>
          <button
            type="button"
            className="apply-confirm-close"
            onClick={onCancel}
          >
            &times;
          </button>
        </div>

        <div className="apply-confirm-body">
          <p>
            Claude Code will apply the{" "}
            <strong>
              {findingCount} selected optimization{findingCount !== 1 ? "s" : ""}
            </strong>{" "}
            directly to your codebase. You'll be able to review all changes
            in your editor before committing anything.
          </p>
          <div className="apply-confirm-warning">
            <span className="apply-confirm-warning-icon" aria-hidden="true">!</span>
            <span>
              Make sure your project is under version control or that you have
              saved any uncommitted changes before proceeding.
            </span>
          </div>
        </div>

        <div className="apply-confirm-footer">
          <button
            type="button"
            className="apply-confirm-cancel"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="apply-confirm-run"
            onClick={onRun}
          >
            Run
          </button>
        </div>
      </div>
    </div>
  );
}
