---
name: themed-commits
description: Splits all uncommitted local changes into ~5 logically themed commits
  and pushes them to remote. Triggers when the user asks to break changes into
  commits, split into commits, or group and push changes.
allowed-tools:
  - Read
  - Bash(git diff)
  - Bash(git diff --cached)
  - Bash(git status)
  - Bash(git log)
  - Bash(git add)
  - Bash(git commit)
  - Bash(git push)
  - Grep
  - Glob
---

## Split Changes into Themed Commits and Push

When triggered, organize all uncommitted changes into ~5 logical commits grouped by theme, then push them.

### Steps

1. Run `git status` and `git diff` to inventory all changes (staged + unstaged + untracked).
2. Read modified files to understand the nature of each change.
3. Group changes into ~5 logical themes. Good grouping criteria:
   - Feature area (e.g., "frontend UI polish", "backend API changes")
   - Type of change (e.g., "bug fixes", "refactoring", "new feature")
   - Related files that form a coherent unit of work
4. Present the proposed commit plan to the user:
   - Commit 1: [theme] - list of files
   - Commit 2: [theme] - list of files
   - ...
5. After user approval, execute each commit sequentially:
   - Stage only the files for that commit
   - Write a clear, concise commit message describing the theme
   - Push after each commit succeeds
6. Run `git status` after the final push to confirm everything is clean.

### Commit message style

- Use imperative mood ("Add", "Fix", "Refactor", not "Added", "Fixed")
- Keep the first line under 72 characters
- Add a blank line and short body if the commit covers multiple related changes

### Important

- Never force-push or amend existing remote commits.
- If any commit fails (e.g., pre-commit hook), stop and report the issue before continuing.
- Ask for confirmation before pushing if you are not confident the changes are production-ready.
