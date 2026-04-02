from analyzers.base import build_agentic_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

You are analyzing a project's custom slash commands (.claude/commands/ directory) for quality
issues and gaps. Custom commands let users invoke project-specific workflows via /project:<name>
in Claude Code. They load on-demand (not every turn), making them the ideal place for workflow
instructions that would otherwise bloat CLAUDE.md.

---

**ISSUE A: No custom commands directory**

If .claude/commands/ does not exist OR is empty, check whether the project has repeatable
workflows that should be commands. Look for evidence in:

- package.json "scripts" section (build, test, lint, deploy, start, dev, format, migrate)
- Makefile, justfile, or Taskfile targets
- CI/CD configs: .github/workflows/, .gitlab-ci.yml, Jenkinsfile, .circleci/
- docker-compose.yml services and commands
- README.md sections describing multi-step processes (deployment, setup, release)
- CLAUDE.md sections describing workflow instructions (these should be commands instead)

If the project has 2 or more repeatable workflows, this is a finding. Suggest 2-4 specific
commands with ready-to-use markdown content tailored to the project. Each suggested command
should include:
- A YAML frontmatter block with a `description` field
- Step-by-step instructions
- Use $ARGUMENTS where the command should accept parameters

Example command format:
```
---
description: Run tests for a specific module or the entire test suite
---
Run the test suite. If $ARGUMENTS is provided, run tests for that specific module/file.
Otherwise, run the full test suite.

Steps:
1. ...
2. ...
```

**ISSUE B: Existing commands missing $ARGUMENTS support**

For each command file in .claude/commands/, check if it hardcodes values that should be
parameterizable. Examples:
- A deploy command that always targets "production" instead of accepting $ARGUMENTS for
  the target environment
- A test command that always runs the full suite instead of accepting a specific test path
- A migration command that always runs all migrations instead of accepting a specific one

**ISSUE C: Content duplicated between CLAUDE.md and commands**

Check if CLAUDE.md contains workflow instructions (deployment steps, testing procedures,
build processes) that also exist as commands or SHOULD be extracted to commands. Content in
CLAUDE.md is loaded on every turn; the same content as a command is loaded only when invoked.
This is a concrete cost reduction.

Read both CLAUDE.md and all command files. Flag sections of CLAUDE.md (>200 tokens on a
specific workflow) that could be extracted to a command, reducing per-turn context.

**ISSUE D: Poor command structure**

For existing commands, check for:
- Over ~2,000 tokens: too long for a focused command. Should be split or trimmed.
- Vague instructions: no step-by-step structure, no clear success criteria.
- Missing description frontmatter: without a `description` field in the YAML frontmatter,
  the command won't show a helpful hint in the /project: autocomplete.
- No clear output specification: the command should describe what "done" looks like.

**ISSUE E: Missing common workflow commands**

Even if some commands exist, check for common gaps based on the project type:
- deploy.md: if the project has deployment infrastructure (Docker, k8s, cloud configs)
- test.md: if the project has a test framework but no test command
- review.md: for code review workflows (check style, run lint, verify types)
- migrate.md: if the project uses database migrations
- setup.md: if the project has complex setup steps (install deps, seed DB, configure env)

Only suggest commands where clear evidence exists in the project.

---

REPORT STRUCTURE:
- For missing commands: location is "." (project root), current_state describes the
  workflows found, suggested_fix shows the command file content.
- For quality issues: location is the specific command file path.
- For duplication: location is CLAUDE.md, current_state shows the duplicated section,
  suggested_fix shows the extracted command.

IMPACT ESTIMATION:
- Missing commands directory: cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"
- Duplicated content: cost_reduction "medium" (removes per-turn load from CLAUDE.md),
  latency_reduction "low", reliability_improvement "low"
- Poor command quality: cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"
- Missing $ARGUMENTS: cost_reduction "low", latency_reduction "low",
  reliability_improvement "low"

CONFIDENCE:
- "high" for missing commands when clear workflows exist
- "high" for missing description frontmatter
- "medium" for content duplication, quality issues, and missing $ARGUMENTS

WHEN NOT TO FLAG:
- If the project is a simple library or script with no multi-step workflows beyond
  basic test/build, and CLAUDE.md is already lean, return [].
- If commands exist, are well-structured, and cover the project's workflows, return [].

DOCS REFERENCES:
- Custom slash commands: https://docs.anthropic.com/en/docs/claude-code/slash-commands
"""


def build_prompt() -> str:
    return build_agentic_base_prompt("commands_quality", ANALYSIS_INSTRUCTIONS)
