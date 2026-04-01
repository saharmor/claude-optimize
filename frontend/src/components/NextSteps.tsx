interface Props {
  selectedCount: number;
}

export default function NextSteps({ selectedCount }: Props) {
  return (
    <section className="next-steps" aria-labelledby="next-steps-title">
      <h2 id="next-steps-title" className="next-steps-heading">
        What to do next
      </h2>
      <ol className="next-steps-list">
        <li className="next-steps-item">
          <span className="next-steps-number">1</span>
          <div className="next-steps-content">
            <h3>Review the findings</h3>
            <p>Browse the results below to understand what can be optimized in your project.</p>
          </div>
        </li>
        <li className={`next-steps-item${selectedCount > 0 ? " next-steps-item-done" : ""}`}>
          <span className="next-steps-number">
            {selectedCount > 0 ? (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M2.5 7.5L5.5 10.5L11.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              "2"
            )}
          </span>
          <div className="next-steps-content">
            <h3>Select which ones to fix</h3>
            <p>
              Use the checkboxes to pick the findings you want to address.
              {selectedCount > 0 && (
                <span className="next-steps-badge">{selectedCount} selected</span>
              )}
            </p>
          </div>
        </li>
        <li className="next-steps-item">
          <span className="next-steps-number">3</span>
          <div className="next-steps-content">
            <h3>Generate a prompt or apply directly</h3>
            <p>
              Copy a ready-made coding prompt into any AI assistant, or let Claude Code apply the fixes for you automatically.
            </p>
          </div>
        </li>
      </ol>
    </section>
  );
}
