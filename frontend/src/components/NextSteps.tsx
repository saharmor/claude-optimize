export default function NextSteps() {
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
        <li className="next-steps-item">
          <span className="next-steps-number">2</span>
          <div className="next-steps-content">
            <h3>Select which ones to fix</h3>
            <p>
              Use the checkboxes to pick the findings you want to address.
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
