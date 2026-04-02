from analyzers.base import build_agentic_base_prompt

ANALYSIS_INSTRUCTIONS = """\
WHAT TO LOOK FOR:

You are analyzing a project for .claudeignore optimization. The .claudeignore file works like
.gitignore: it tells Claude Code which files and directories to skip when reading the project.
Without it, Claude may waste context reading build artifacts, dependency directories, binary
files, generated code, and other content that adds no value to code analysis.

---

**ISSUE A: Missing .claudeignore**

If NO .claudeignore file exists at the project root, check whether the project has content
that should be excluded. Look for ANY of these:

Build artifacts and output directories:
- build/, dist/, out/, .next/, .nuxt/, .output/, target/, __pycache__/, *.pyc
- .gradle/, .mvn/, bin/, obj/, Release/, Debug/

Dependency directories:
- node_modules/, .venv/, venv/, env/, .env/, vendor/, third_party/, bower_components/

Generated and compiled files:
- Large lockfiles: package-lock.json, yarn.lock, pnpm-lock.yaml, poetry.lock, Cargo.lock,
  Gemfile.lock, composer.lock (these can be thousands of lines)
- Auto-generated code: protobuf output, GraphQL codegen, OpenAPI clients, compiled CSS/JS
- Source maps: *.map files

Binary and media assets:
- Images: *.png, *.jpg, *.jpeg, *.gif, *.ico, *.svg (if many), *.webp
- Fonts: *.woff, *.woff2, *.ttf, *.eot
- Videos/audio: *.mp4, *.mp3, *.wav
- Documents: *.pdf (if many)
- Compiled binaries: *.so, *.dylib, *.dll, *.exe, *.wasm

Test and coverage output:
- coverage/, .nyc_output/, htmlcov/, .pytest_cache/, jest-cache/

If the project has ANY of the above, this is a finding. Generate a complete, ready-to-use
.claudeignore file tailored to the project's actual directory structure and tech stack.

**ISSUE B: Incomplete .claudeignore**

If .claudeignore exists, check whether it's missing obvious exclusions for directories and
files that actually exist in the project. Cross-reference the patterns above against the
actual project contents. Common gaps:
- Node.js project without node_modules/ or lockfile exclusion
- Python project without __pycache__/, .venv/, or *.pyc
- Next.js project without .next/
- Rust project without target/
- Java/Kotlin project without build/ or .gradle/
- Go project without vendor/ (if vendored)

Flag specific missing exclusions with evidence (the directory/file exists in the project).

**ISSUE C: Overly broad .claudeignore**

If .claudeignore has patterns that accidentally exclude files Claude SHOULD see:
- Excluding all of src/, lib/, or app/
- Excluding *.ts, *.py, *.js, or other source file extensions
- Excluding config files that are relevant to the project structure
- Excluding .claude/ directory itself

This is a separate finding. Show the problematic patterns and suggest corrections.

---

REPORT STRUCTURE:
- For missing .claudeignore: location should be "." (project root), current_state should
  describe what excludable content was found, suggested_fix should be a complete .claudeignore.
- For incomplete: location should be ".claudeignore", show current content and what's missing.
- For overly broad: location should be ".claudeignore", show the problematic patterns.

IMPACT ESTIMATION:
- Missing .claudeignore: cost_reduction "medium", latency_reduction "low",
  reliability_improvement "medium"
- Incomplete: cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"
- Overly broad: cost_reduction "low", latency_reduction "low",
  reliability_improvement "medium"

CONFIDENCE:
- "high" for missing .claudeignore when excludable content exists
- "high" for overly broad patterns
- "medium" for incomplete (requires judgment about what's relevant)

WHEN NOT TO FLAG:
- If the project is very small (fewer than ~20 files) with no build artifacts,
  dependencies, or binary assets, return [].
- If .claudeignore exists and covers all relevant patterns, return [].

DOCS REFERENCES:
- .claudeignore: https://docs.anthropic.com/en/docs/claude-code/memory#claudeignore
"""


def build_prompt() -> str:
    return build_agentic_base_prompt("claudeignore_quality", ANALYSIS_INSTRUCTIONS)
