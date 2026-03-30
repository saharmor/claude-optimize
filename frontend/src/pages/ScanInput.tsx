import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRecentProjects, startScan } from "../api/client";
import claudeLogo from "../assets/claude-logo.svg";
import { Button, PageIntro, Surface } from "../components/ui";
import type { RecentProject } from "../types/scan";

export default function ScanInput() {
  const navigate = useNavigate();
  const [recentProjects, setRecentProjects] = useState<RecentProject[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [manualMode, setManualMode] = useState(false);
  const [selectedProjectPath, setSelectedProjectPath] = useState("");
  const [projectPath, setProjectPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const loadRecentProjects = async () => {
      try {
        const projects = await getRecentProjects();
        if (cancelled) return;
        setRecentProjects(projects);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to fetch recent projects"
          );
        }
      } finally {
        if (!cancelled) {
          setProjectsLoading(false);
        }
      }
    };

    void loadRecentProjects();

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedProject = useMemo(
    () =>
      recentProjects.find((project) => project.path === selectedProjectPath) ?? null,
    [recentProjects, selectedProjectPath]
  );
  const hasRecentProjects = recentProjects.length > 0;
  const showRecentProjectPicker = hasRecentProjects && !manualMode;
  const showManualFields = manualMode || (!projectsLoading && !hasRecentProjects);

  const handleRecentProjectChange = (
    e: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const nextPath = e.target.value;
    setManualMode(false);
    setSelectedProjectPath(nextPath);
    setError("");

    const project = recentProjects.find((candidate) => candidate.path === nextPath);
    if (!project) {
      return;
    }

    setProjectPath(project.path);
  };

  const handleManualEntry = () => {
    setSelectedProjectPath("");
    setManualMode(true);
    setError("");
  };

  const handleUseRecentProjects = () => {
    setManualMode(false);
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectPath.trim()) return;

    setLoading(true);
    setError("");

    try {
      const { scan_id } = await startScan(projectPath.trim());
      navigate(`/report/${scan_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start optimization audit");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="landing-layout">
      <div className="landing-hero">
        <div className="landing-copy">
          <img src={claudeLogo} alt="Claude logo" width={96} height={96} />
          <PageIntro
            eyebrow=""
            title="Optimize your Claude integration in minutes."
            description="Get a prioritized and actionable optimization audit for cost, latency, and reliability improvements."
          />
        </div>

        <Surface className="form-surface">
          <form onSubmit={handleSubmit} className="form-layout">
            <PageIntro
              eyebrow=""
              title="Audit a local project"
              description="Point to any project that uses Claude and get an actionable optimization audit in under a minute."
              size="subsection"
              className="form-heading"
            />

            {projectsLoading && !manualMode && (
              <div className="form-actions form-actions-inline">
                <p className="form-footnote">
                  Looking for recent local projects you worked on.
                </p>
                <div className="project-input-actions">
                  <button
                    type="button"
                    className="project-input-text-action"
                    onClick={handleManualEntry}
                    disabled={loading}
                  >
                    Or enter manually
                  </button>
                </div>
              </div>
            )}

            {showRecentProjectPicker && (
              <>
                <div className="form-group">
                  <select
                    id="recent-project"
                    aria-label="Select a recent project"
                    className="input-field"
                    value={selectedProjectPath}
                    onChange={handleRecentProjectChange}
                    disabled={loading}
                  >
                    <option value="">Select a recent project</option>
                    {recentProjects.map((project) => (
                      <option key={project.path} value={project.path}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="selected-project-slot" aria-live="polite">
                  <div
                    className={`selected-project-card${
                      selectedProject ? "" : " selected-project-card-placeholder"
                    }`}
                  >
                    <div className="selected-project-path">
                      {selectedProject?.path ??
                        "Choose a recent project to preview its local path before running the audit."}
                    </div>
                  </div>
                </div>

                <div className="project-input-actions">
                  <button
                    type="button"
                    className="project-input-text-action"
                    onClick={handleManualEntry}
                    disabled={loading}
                  >
                    Or enter manually
                  </button>
                </div>
              </>
            )}

            {showManualFields && (
              <>
                {hasRecentProjects && (
                  <div className="project-input-actions">
                    <Button
                      type="button"
                      variant="secondary"
                      className="btn-compact"
                      onClick={handleUseRecentProjects}
                      disabled={loading}
                    >
                      Choose recent project
                    </Button>
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="project-path">Project path</label>
                  <input
                    id="project-path"
                    className="input-field"
                    type="text"
                    placeholder="/path/to/your/claude-powered/project"
                    value={projectPath}
                    onChange={(e) => {
                      const nextValue = e.target.value;
                      setProjectPath(nextValue);
                      if (selectedProjectPath && nextValue !== selectedProjectPath) {
                        setSelectedProjectPath("");
                      }
                    }}
                    disabled={loading}
                  />
                  <span className="hint">
                    Absolute path to the project directory you want Claude Optimize
                    to inspect.
                  </span>
                </div>
              </>
            )}

            {error && <div className="error-message">{error}</div>}

            <div className="form-actions">
              <Button
                type="submit"
                variant="primary"
                disabled={loading || !projectPath.trim()}
              >
                {loading ? (
                  <>
                    <span className="spinner" /> Starting audit...
                  </>
                ) : (
                  "Run Audit"
                )}
              </Button>
              <p className="form-footnote">
                Tip: the sample project is available in the picker if you want to
                preview a full example audit.
              </p>
            </div>
          </form>
        </Surface>
      </div>

      <div className="landing-steps">
        <div className="step-card">
          <span className="step-icon" aria-hidden="true">
            ↓
          </span>
          <div className="step-content">
            <h3>Cut API costs up to 80%</h3>
            <p>
              Most Claude integrations miss prompt caching, batching, and
              structured output features that are already available. One audit
              finds every opportunity.
            </p>
          </div>
        </div>
        <div className="step-card">
          <span
            className="step-icon step-icon-clipboard"
            aria-hidden="true"
          />
          <div className="step-content">
            <h3>Copy-paste fixes</h3>
            <p>
              Every finding includes the exact code from your repo, a
              ready-to-use fix, and a link to the relevant Anthropic docs.
            </p>
          </div>
        </div>
        <div className="step-card">
          <span className="step-icon" aria-hidden="true">
            <img src={claudeLogo} alt="" className="step-icon-logo" />
          </span>
          <div className="step-content">
            <h3>Powered by Claude Code</h3>
            <p>
              Five parallel Claude Code sessions, each with specialized
              analysis prompts written by Anthropic's engineers.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
