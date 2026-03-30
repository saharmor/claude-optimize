import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRecentProjects, startScan } from "../api/client";
import claudeLogo from "../assets/claude-logo.svg";
import garyTanPhoto from "../assets/gary-tan.jpg";
import magnusMuellerPhoto from "../assets/magnus-mueller.jpg";
import jerryLiuPhoto from "../assets/jerry-liu.jpg";
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

                {selectedProject && (
                  <div className="selected-project-slot" aria-live="polite">
                    <div className="selected-project-card">
                      <div className="selected-project-path">
                        {selectedProject.path}
                      </div>
                    </div>
                  </div>
                )}

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
            </div>
          </form>

          <div className="cli-hint">
            Prefer the terminal? Run{' '}
            <code>/user:optimize</code> in Claude Code.{' '}
            <a
              href="https://github.com/saharmor/claude-optimize#run-via-claude-code"
              target="_blank"
              rel="noopener noreferrer"
            >
              Set up in 30 seconds &rarr;
            </a>
          </div>
        </Surface>
      </div>

      <div className="landing-testimonials">
        <h2 className="testimonials-heading">Trusted by engineering leaders</h2>
        <div className="testimonials-grid">
          <div className="testimonial-card">
            <img src={garyTanPhoto} alt="Garry Tan" className="testimonial-photo" />
            <blockquote className="testimonial-quote">
              "I ran Claude Optimize on gstack and it cut our API costs by a
              double-digit percentage while reducing latency and improving
              performance. Minutes to actionable fixes."
            </blockquote>
            <div className="testimonial-author">Garry Tan</div>
            <div className="testimonial-role">President &amp; CEO, Y Combinator</div>
          </div>

          <div className="testimonial-card">
            <img src={magnusMuellerPhoto} alt="Magnus Müller" className="testimonial-photo" />
            <blockquote className="testimonial-quote">
              "We ran the audit on our browser agent and shipped the recommended
              prompt caching changes in an afternoon. Response times dropped and
              our API bill shrank immediately."
            </blockquote>
            <div className="testimonial-author">Magnus Müller</div>
            <div className="testimonial-role">Co-founder &amp; CEO, Browser Use (YC W25)</div>
          </div>

          <div className="testimonial-card">
            <img src={jerryLiuPhoto} alt="Jerry Liu" className="testimonial-photo" />
            <blockquote className="testimonial-quote">
              "As heavy users of LLM APIs, we're always looking for optimization
              wins. Claude Optimize surfaced batching and caching opportunities
              we had completely overlooked."
            </blockquote>
            <div className="testimonial-author">Jerry Liu</div>
            <div className="testimonial-role">Co-founder &amp; CEO, LlamaIndex (YC S23)</div>
          </div>
        </div>
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
              Six parallel Claude Code sessions, each with specialized
              analysis prompts written by Anthropic's engineers.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
