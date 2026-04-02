from analyzers.base import build_agentic_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

You are analyzing a project's Claude Code settings and permission configuration for security
risks, missing guardrails, and configuration gaps. Settings control what Claude Code can and
cannot do in this project. Misconfigured permissions create security risks; missing permissions
cause unnecessary friction with constant approval prompts.

Check project-level files ONLY (not the user's home directory ~/.claude/):
- .claude/settings.json (committed to version control, shared with team)
- .claude/settings.local.json (gitignored, per-developer overrides)

Also check:
- .gitignore (to see if .claude/ is excluded)
- .env files (to detect environment variable usage)
- Project files for infrastructure, deployment, and security context

---

**ISSUE A: Missing settings file**

If .claude/settings.json does not exist, this is a finding for any non-trivial project.
Even basic projects benefit from explicit permission rules. Examine the project's tech stack
and suggest a starter settings.json with:
- Reasonable allow rules for read-only tools (Read, Glob, Grep)
- Allow rules for safe project-specific commands (the test runner, linter, etc.)
- Deny rules for dangerous operations relevant to this project

**ISSUE B: Overly permissive permissions**

Look for overly broad patterns in the "allow" list:
- "Bash(**)" or "Bash(*)" -- allows ANY shell command without approval
- "Edit(**)" or "Write(**)" -- allows editing any file without approval
- Patterns that grant blanket access when only specific commands are needed

Recommend scoping to specific safe commands based on the project's actual toolchain.
For example, replace "Bash(**)" with specific commands like:
  ["Bash(npm test)", "Bash(npm run lint)", "Bash(git status)", "Bash(git diff)"]

**ISSUE C: Missing deny rules for dangerous operations**

Check if the project has files or infrastructure that warrant protective deny rules, but
no deny rules are configured. Only flag this if relevant files actually exist:

- Git destructive ops: if it's a git repo, consider deny for "git push --force",
  "git reset --hard", "git clean -f"
- Database: if project has database configs (prisma/, migrations/, .sql files, database URLs),
  consider deny for DROP, DELETE FROM, TRUNCATE
- Package publishing: if package.json has "publishConfig" or "private: false", or if
  setup.py/pyproject.toml has publishing metadata, consider deny for "npm publish",
  "pip upload", "cargo publish"
- Infrastructure: if project has Terraform files, k8s manifests, or AWS configs,
  consider deny for "terraform destroy", "kubectl delete"
- File deletion: consider deny for "rm -rf" in projects with important data directories

Do NOT flag this generically. Only flag when the project has actual infrastructure that
would be damaged by these commands.

**ISSUE D: Secrets in committed settings file**

Check .claude/settings.json for values that look like secrets:
- Environment variables in the "env" section with names containing: TOKEN, KEY, SECRET,
  PASSWORD, CREDENTIAL, AUTH, API_KEY
- MCP server configurations with hardcoded tokens or passwords in their "env" section
- Any string values that look like API keys (long alphanumeric strings, base64, etc.)

These should be in .claude/settings.local.json (which is gitignored) instead of the
committed settings.json. Show what to move and where.

**ISSUE E: .claude/ directory excluded from version control**

Check .gitignore for patterns that exclude the entire .claude/ directory:
- ".claude/" or ".claude" or ".claude/*"

If found, this prevents the team from sharing Claude Code configuration. The recommended
pattern is to commit .claude/settings.json and .claude/commands/ while gitignoring only
.claude/settings.local.json (for per-developer secrets and overrides).

Suggest the correct .gitignore pattern:
```
.claude/settings.local.json
```

**ISSUE F: Missing environment variable configuration**

Check if the project uses environment variables (evidence: .env files, dotenv imports,
process.env references, os.environ usage) but .claude/settings.json has no "env" section.

When Claude Code runs the project (tests, dev server, etc.), it needs these env vars.
Without them configured in settings, Claude Code sessions will fail or behave unexpectedly.

Suggest adding an "env" section to settings.json with the variable names (but NOT the
actual values, which should go in settings.local.json).

---

REPORT STRUCTURE:
- For missing settings: location is ".claude/", suggested_fix is a complete settings.json.
- For permission issues: location is ".claude/settings.json", show the problematic rules.
- For secrets: location is ".claude/settings.json", show what needs to move to settings.local.json.
- For .gitignore issues: location is ".gitignore".

IMPACT ESTIMATION:
- Overly permissive (B): cost_reduction "low", latency_reduction "low",
  reliability_improvement "high"
- Missing deny rules (C): cost_reduction "low", latency_reduction "low",
  reliability_improvement "high"
- Secrets exposed (D): cost_reduction "low", latency_reduction "low",
  reliability_improvement "high"
- Missing settings (A): cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"
- Gitignore issue (E): cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"
- Missing env config (F): cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"

CONFIDENCE:
- "high" for Issues B, D (pattern-matchable, objectively verifiable)
- "medium" for Issues A, C, E, F (requires judgment about project needs)

WHEN NOT TO FLAG:
- If settings.json exists with reasonably scoped permissions, no secrets in committed
  files, appropriate deny rules, and .claude/ is not entirely gitignored, return [].
- If the project is a simple script with no infrastructure, don't flag missing deny rules.

DOCS REFERENCES:
- Claude Code settings: https://docs.anthropic.com/en/docs/claude-code/settings
- Permissions: https://docs.anthropic.com/en/docs/claude-code/security
"""


def build_prompt() -> str:
    return build_agentic_base_prompt("settings_permissions", ANALYSIS_INSTRUCTIONS)
