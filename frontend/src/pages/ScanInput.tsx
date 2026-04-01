import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cloneRepo, getConfig, getRecentProjects, startScan } from "../api/client";
import claudeLogo from "../assets/claude-logo.svg";
import garyTanPhoto from "../assets/gary-tan.jpg";
import magnusMuellerPhoto from "../assets/magnus-mueller.jpg";
import jerryLiuPhoto from "../assets/jerry-liu.jpg";
import { Button, PageIntro, Surface } from "../components/ui";
import type { RecentProject } from "../types/scan";

function GitHubIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M1.75 1A1.75 1.75 0 000 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0016 13.25v-8.5A1.75 1.75 0 0014.25 3H7.5a.25.25 0 01-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1H1.75z" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M8 1.5a6.5 6.5 0 110 13 6.5 6.5 0 010-13zM8 0a8 8 0 100 16A8 8 0 008 0zm.5 4.75a.75.75 0 00-1.5 0v3.5a.75.75 0 00.37.65l2.5 1.5a.75.75 0 10.76-1.3L8.5 7.82V4.75z" />
    </svg>
  );
}

type InputMethod = "recent" | "clone" | "path";

export default function ScanInput() {
  const navigate = useNavigate();
  const [recentProjects, setRecentProjects] = useState<RecentProject[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [activeMethod, setActiveMethod] = useState<InputMethod>("recent");
  const [selectedProjectPath, setSelectedProjectPath] = useState("");
  const [projectPath, setProjectPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showGithubClone, setShowGithubClone] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [cloneDestination, setCloneDestination] = useState("");
  const [cloning, setCloning] = useState(false);

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

    const loadConfig = async () => {
      try {
        const config = await getConfig();
        if (!cancelled) {
          setShowGithubClone(config.show_github_clone);
        }
      } catch {
        // Config fetch failed; keep defaults
      }
    };

    void loadRecentProjects();
    void loadConfig();

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

  // Once projects load, if there are none, default to "path" tab
  useEffect(() => {
    if (!projectsLoading && !hasRecentProjects && activeMethod === "recent") {
      setActiveMethod("path");
    }
  }, [projectsLoading, hasRecentProjects, activeMethod]);

  const handleTabChange = (method: InputMethod) => {
    setActiveMethod(method);
    setError("");
  };

  const handleRecentProjectChange = (
    e: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const nextPath = e.target.value;
    setSelectedProjectPath(nextPath);
    setError("");

    const project = recentProjects.find((candidate) => candidate.path === nextPath);
    if (!project) return;
    setProjectPath(project.path);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    let scanPath = projectPath.trim();

    if (activeMethod === "clone") {
      if (!githubUrl.trim() || !cloneDestination.trim()) return;

      setCloning(true);
      try {
        const { path } = await cloneRepo(githubUrl.trim(), cloneDestination.trim());
        scanPath = path;
        setProjectPath(path);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to clone repository");
        setCloning(false);
        return;
      }
      setCloning(false);
    }

    if (!scanPath) return;

    setLoading(true);
    try {
      const { scan_id } = await startScan(scanPath);
      navigate(`/report/${scan_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start optimization audit");
    } finally {
      setLoading(false);
    }
  };

  const busy = loading || cloning;

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

            {/* ── Tab bar ── */}
            <div className="input-method-tabs" role="tablist">
              {hasRecentProjects && (
                <button
                  type="button"
                  id="tab-recent"
                  role="tab"
                  aria-selected={activeMethod === "recent"}
                  aria-controls="panel-recent"
                  className={`input-method-tab${activeMethod === "recent" ? " input-method-tab--active" : ""}`}
                  onClick={() => handleTabChange("recent")}
                  disabled={busy}
                >
                  <ClockIcon /> Recent project
                </button>
              )}
              {showGithubClone && (
                <button
                  type="button"
                  id="tab-clone"
                  role="tab"
                  aria-selected={activeMethod === "clone"}
                  aria-controls="panel-clone"
                  className={`input-method-tab${activeMethod === "clone" ? " input-method-tab--active" : ""}`}
                  onClick={() => handleTabChange("clone")}
                  disabled={busy}
                >
                  <GitHubIcon /> Clone
                </button>
              )}
              <button
                type="button"
                id="tab-path"
                role="tab"
                aria-selected={activeMethod === "path"}
                aria-controls="panel-path"
                className={`input-method-tab${activeMethod === "path" ? " input-method-tab--active" : ""}`}
                onClick={() => handleTabChange("path")}
                disabled={busy}
              >
                <FolderIcon /> Enter path
              </button>
            </div>

            {/* ── Recent project panel ── */}
            {activeMethod === "recent" && (
              <div role="tabpanel" id="panel-recent" aria-labelledby="tab-recent">
                {projectsLoading ? (
                  <p className="form-footnote">
                    Looking for recent local projects you worked on...
                  </p>
                ) : (
                  <>
                    <div className="form-group">
                      <select
                        id="recent-project"
                        aria-label="Select a recent project"
                        className="input-field"
                        value={selectedProjectPath}
                        onChange={handleRecentProjectChange}
                        disabled={busy}
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
                  </>
                )}
              </div>
            )}

            {/* ── Clone panel ── */}
            {activeMethod === "clone" && (
              <div role="tabpanel" id="panel-clone" aria-labelledby="tab-clone">
                <div className="form-group">
                  <label htmlFor="github-url">GitHub URL</label>
                  <input
                    id="github-url"
                    className="input-field"
                    type="text"
                    placeholder="https://github.com/owner/repo"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    disabled={busy}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="clone-destination">Clone destination</label>
                  <input
                    id="clone-destination"
                    className="input-field"
                    type="text"
                    placeholder="/path/to/clone/into"
                    value={cloneDestination}
                    onChange={(e) => setCloneDestination(e.target.value)}
                    disabled={busy}
                  />
                  <span className="hint">
                    Absolute path where the repository will be cloned.
                  </span>
                </div>
              </div>
            )}

            {/* ── Enter path panel ── */}
            {activeMethod === "path" && (
              <div role="tabpanel" id="panel-path" aria-labelledby="tab-path">
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
                    disabled={busy}
                  />
                  <span className="hint">
                    Absolute path to the project directory you want Claude Optimize
                    to inspect.
                  </span>
                </div>
              </div>
            )}

            {error && <div className="error-message">{error}</div>}

            <div className="form-actions">
              <Button
                type="submit"
                variant="primary"
                disabled={
                  busy ||
                  (activeMethod === "clone"
                    ? !githubUrl.trim() || !cloneDestination.trim()
                    : !projectPath.trim())
                }
              >
                {cloning ? (
                  <>
                    <span className="spinner" /> Cloning repository...
                  </>
                ) : loading ? (
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
        <h2 className="testimonials-heading">Why teams use Claude Optimize</h2>
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
              Eight parallel Claude Code sessions, each with specialized
              analysis prompts written by Anthropic's engineers.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
