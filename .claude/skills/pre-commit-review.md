---
name: pre-commit-review
description: Thoroughly reviews all uncommitted local changes and generates a
  prioritized report of bugs, inefficiencies, and code debris. Triggers when the
  user says they want to review changes before committing or pushing.
allowed-tools:
  - Read
  - Bash(git diff)
  - Bash(git diff --cached)
  - Bash(git status)
  - Bash(git log)
  - Grep
  - Glob
---

## Pre-Commit Code Review

When triggered, perform a senior-engineer-level review of every uncommitted change in the repository.

### Steps

1. Run `git status` and `git diff` (both staged and unstaged) to understand the full scope of changes.
2. Read each modified file to understand the context around every change.
3. Produce a single prioritized report with three sections:

#### P0 - Bugs
Things that will not work as expected or currently break functionality.
- Check for logic errors, missing edge cases, broken imports, type mismatches.
- Check for regressions where a recent change may have undone earlier work.

#### P1 - Inefficiencies
Things done in a suboptimal way where a better approach exists.
- Redundant API calls, unnecessary re-renders, N+1 queries.
- Overly complex logic that could be simplified.

#### P2 - Code Redundancies and Debris
Leftover code, dead references, naming inconsistencies.
- Unused imports, variables, or functions.
- Old naming conventions that should have been updated.
- Stale comments or TODOs that no longer apply.

### Output format

Present each item as a numbered list within its section, with:
- The file and line range
- A one-sentence description of the issue
- Severity within the category (critical / moderate / minor)

After presenting the report, ask the user which items they want fixed before committing.

### Important
- Never use em dashes in any output text.
- Do not auto-fix anything without user approval.
- Focus on real issues with high confidence, not speculative style nitpicks.
