from __future__ import annotations

import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)

_CMD_TIMEOUT = 30  # seconds per git command
_PUSH_TIMEOUT = 60  # seconds for push (network-bound)


async def _run_git(
    args: list[str],
    cwd: str,
    timeout: int = _CMD_TIMEOUT,
) -> str:
    """Run a git/gh command and return its stdout. Raises on failure."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"Command timed out: {' '.join(args)}")

    if proc.returncode != 0:
        err = stderr.decode().strip() if stderr else "unknown error"
        raise RuntimeError(f"`{' '.join(args)}` failed: {err}")

    return stdout.decode().strip() if stdout else ""


async def _run_git_ok(
    args: list[str],
    cwd: str,
    timeout: int = _CMD_TIMEOUT,
) -> tuple[bool, str, str]:
    """Run a git command and return (success, stdout, stderr) without raising."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, "", "Command timed out"

    out = stdout.decode().strip() if stdout else ""
    err = stderr.decode().strip() if stderr else ""
    return proc.returncode == 0, out, err


async def _ensure_push_remote(
    project_path: str,
    branch_name: str,
    on_output: Callable[[str], None] | None = None,
) -> tuple[str, str | None]:
    """Determine which remote to push to, forking if necessary.

    Returns (remote_name, gh_pr_head_flag_value).
    - For repos the user owns/has write access: ("origin", None)
    - For forked repos: ("fork", "<user>:<branch>")
    """
    def _log(msg: str) -> None:
        if on_output:
            on_output(msg)

    # Try a dry-run push to origin to check permissions
    ok, _, err = await _run_git_ok(
        ["git", "push", "--dry-run", "origin", branch_name],
        cwd=project_path,
        timeout=_PUSH_TIMEOUT,
    )
    if ok:
        return "origin", None

    # Permission denied — need to fork
    if "403" in err or "permission" in err.lower() or "denied" in err.lower():
        _log("No push access to origin. Forking repository...")

        # gh repo fork --remote adds a "fork" remote pointing to user's fork
        await _run_git(
            ["gh", "repo", "fork", "--remote", "--remote-name", "fork"],
            cwd=project_path,
            timeout=_PUSH_TIMEOUT,
        )

        # Get the authenticated user's GitHub username for --head flag
        gh_user = await _run_git(
            ["gh", "api", "user", "--jq", ".login"],
            cwd=project_path,
        )

        return "fork", f"{gh_user}:{branch_name}"

    # Some other push error — raise it
    raise RuntimeError(f"Push failed: {err}")


async def snapshot_changed_files(project_path: str) -> set[str]:
    """Return the set of files currently modified/untracked in the working tree.

    Called BEFORE the apply so we can diff afterward to find only the files
    that Claude changed.
    """
    # Tracked files with modifications (staged or unstaged)
    dirty = await _run_git(
        ["git", "diff", "--name-only", "HEAD"], cwd=project_path
    )
    staged = await _run_git(
        ["git", "diff", "--name-only", "--cached"], cwd=project_path
    )
    # Untracked files
    untracked = await _run_git(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=project_path
    )

    files: set[str] = set()
    for output in (dirty, staged, untracked):
        for line in output.splitlines():
            stripped = line.strip()
            if stripped:
                files.add(stripped)
    return files


async def get_changed_files(project_path: str, before: set[str]) -> list[str]:
    """Return files changed by the apply (new or modified since *before* snapshot)."""
    after = await snapshot_changed_files(project_path)
    # Files that are dirty now but weren't before the apply
    return sorted(after - before)


async def retry_pull_request(
    project_path: str,
    branch_name: str,
    pr_title: str,
    pr_body: str,
    on_output: Callable[[str], None] | None = None,
) -> str:
    """Re-attempt push + PR creation on an existing local branch.

    Assumes the branch already exists with committed changes.
    Returns the PR URL on success. Raises on failure.
    """
    def _log(msg: str) -> None:
        if on_output:
            on_output(msg)

    # Verify gh CLI is available
    try:
        await _run_git(["gh", "--version"], cwd=project_path)
    except (RuntimeError, FileNotFoundError):
        raise RuntimeError(
            "GitHub CLI (gh) is not installed or not in PATH. "
            "Install it from https://cli.github.com to enable PR creation."
        )

    # Verify the branch exists
    try:
        await _run_git(["git", "rev-parse", "--verify", branch_name], cwd=project_path)
    except RuntimeError:
        raise RuntimeError(f"Branch {branch_name} not found locally. Cannot retry.")

    # Determine push remote (fork if no write access to origin)
    remote, head_flag = await _ensure_push_remote(
        project_path, branch_name, on_output=on_output,
    )

    # Push to remote
    _log(f"Pushing to {remote}...")
    await _run_git(
        ["git", "push", "-u", remote, branch_name],
        cwd=project_path,
        timeout=_PUSH_TIMEOUT,
    )

    # Create PR via GitHub CLI
    _log("Creating pull request...")
    pr_cmd = [
        "gh", "pr", "create",
        "--title", pr_title,
        "--body", pr_body,
    ]
    if head_flag:
        pr_cmd += ["--head", head_flag]
    else:
        pr_cmd += ["--head", branch_name]

    pr_url = await _run_git(
        pr_cmd,
        cwd=project_path,
        timeout=_PUSH_TIMEOUT,
    )

    _log(f"Pull request created: {pr_url}")
    return pr_url


async def create_pull_request(
    project_path: str,
    branch_name: str,
    pr_title: str,
    pr_body: str,
    changed_files: list[str],
    on_output: Callable[[str], None] | None = None,
) -> str:
    """Create a branch, commit only *changed_files*, push, and open a GitHub PR.

    Returns the PR URL on success. Raises on failure.
    """
    if not changed_files:
        raise RuntimeError("No changed files to commit")

    def _log(msg: str) -> None:
        if on_output:
            on_output(msg)

    # Verify gh CLI is available
    try:
        await _run_git(["gh", "--version"], cwd=project_path)
    except (RuntimeError, FileNotFoundError):
        raise RuntimeError(
            "GitHub CLI (gh) is not installed or not in PATH. "
            "Install it from https://cli.github.com to enable PR creation."
        )

    # 1. Capture the current branch so we can switch back later
    original_branch = await _run_git(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_path
    )

    created_branch = False
    try:
        # 2. Create and switch to a new branch
        _log(f"Creating branch {branch_name}...")
        await _run_git(["git", "checkout", "-b", branch_name], cwd=project_path)
        created_branch = True

        # 3. Stage ONLY the files changed by the apply
        #    Some files (e.g. .claude/settings.json) may live in gitignored dirs.
        #    Use --force only for those specific files to avoid accidentally
        #    staging secrets or build artifacts.
        _log("Staging changes...")
        ignored_files: list[str] = []
        normal_files: list[str] = []
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "check-ignore", "--", *changed_files,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=_CMD_TIMEOUT)
            ignored_set = set(stdout.decode().strip().splitlines())
            for f in changed_files:
                if f in ignored_set:
                    ignored_files.append(f)
                else:
                    normal_files.append(f)
        except (asyncio.TimeoutError, Exception):
            # If check-ignore fails, treat all as normal (safe default)
            normal_files = changed_files

        if normal_files:
            await _run_git(["git", "add", "--"] + normal_files, cwd=project_path)
        if ignored_files:
            logger.info("Force-staging gitignored files: %s", ignored_files)
            await _run_git(["git", "add", "--force", "--"] + ignored_files, cwd=project_path)

        # 4. Check there are actual staged changes to commit
        check = await asyncio.create_subprocess_exec(
            "git", "diff", "--cached", "--quiet",
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await check.communicate()
        if check.returncode == 0:
            raise RuntimeError("No changes detected to commit")

        # 5. Commit
        _log("Committing changes...")
        await _run_git(
            ["git", "commit", "-m", pr_title], cwd=project_path
        )

        # 6. Determine push remote (fork if no write access to origin)
        remote, head_flag = await _ensure_push_remote(
            project_path, branch_name, on_output=on_output,
        )

        # 7. Push to remote
        _log(f"Pushing to {remote}...")
        await _run_git(
            ["git", "push", "-u", remote, branch_name],
            cwd=project_path,
            timeout=_PUSH_TIMEOUT,
        )

        # 8. Create PR via GitHub CLI
        _log("Creating pull request...")
        pr_cmd = [
            "gh", "pr", "create",
            "--title", pr_title,
            "--body", pr_body,
        ]
        if head_flag:
            pr_cmd += ["--head", head_flag]
        else:
            pr_cmd += ["--head", branch_name]

        pr_url = await _run_git(
            pr_cmd,
            cwd=project_path,
            timeout=_PUSH_TIMEOUT,
        )

        _log(f"Pull request created: {pr_url}")
        return pr_url

    except Exception as exc:
        # Keep the branch and commit so changes are preserved locally.
        # Only clean up if we never got past committing (nothing to preserve).
        if created_branch:
            try:
                # Check if we committed anything on this branch
                has_commit = False
                try:
                    log = await _run_git(
                        ["git", "log", "--oneline", f"{original_branch}..{branch_name}", "--"],
                        cwd=project_path,
                    )
                    has_commit = bool(log.strip())
                except Exception:
                    pass

                if has_commit:
                    # Committed changes exist — switch back but keep the branch
                    logger.info(
                        "Keeping branch %s with committed changes (push/PR failed: %s)",
                        branch_name, exc,
                    )
                    await _run_git(
                        ["git", "checkout", original_branch], cwd=project_path
                    )
                else:
                    # Nothing committed — safe to delete
                    await _run_git(
                        ["git", "checkout", original_branch], cwd=project_path
                    )
                    await _run_git(
                        ["git", "branch", "-D", branch_name], cwd=project_path
                    )
            except Exception:
                logger.warning("Failed to clean up branch %s", branch_name)
        raise

    finally:
        # 8. Switch back to original branch (no-op if already switched in except)
        try:
            current = await _run_git(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_path
            )
            if current != original_branch:
                await _run_git(
                    ["git", "checkout", original_branch], cwd=project_path
                )
        except Exception:
            logger.warning("Failed to switch back to branch %s", original_branch)
