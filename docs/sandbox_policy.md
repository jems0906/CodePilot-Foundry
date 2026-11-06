# Runbook: Add an Allowed Sandbox Command

Compose intentionally exposes one fixed container command (`pytest -q tests`). Local development retains a narrow subprocess policy in `backend/app/sandbox/policy.py`. Adding a binary expands the execution boundary; do not add one to make a demo convenient.

1. State the user task that requires the command and why an existing allowed command cannot satisfy it.
2. For local-only development, add the executable's canonical basename to `CommandPolicy.ALLOWED_BINARIES` in `backend/app/sandbox/policy.py`. Do not change the Compose runner command without a separate threat review.
3. Add command-specific subcommand/argument rules. Reject absolute paths, `..` path components, NUL bytes, and any working directory outside the resolved workspace. Never enable shell parsing.
4. Confirm local execution still uses `shell=False`, a filtered environment, output redaction, timeout, and bounded review-facing output. For Compose, keep the runner command fixed and preserve the no-network, read-only-rootfs, non-root, dropped-capability, and resource-limit settings in `sandbox_runner/app/main.py`.
5. Add positive and negative policy tests. At minimum test an allowed invocation, a disallowed subcommand, traversal, an absolute path, and an external working directory.
6. Add an execution test that exercises the real binary inside a temporary synthetic workspace. Cover timeout and output capture if they apply.
7. Run `python -m pytest backend/tests -q` from the repository root only if the test configuration supports it; the canonical command is `cd backend; python -m pytest tests -q`.
8. Update this runbook and the security section of the README with the new command and its limits.

Never allow a general-purpose shell, interpreter, package manager, or arbitrary binary. The Compose test container is ephemeral but shares the host kernel; the runner's Docker socket is a privileged control-plane boundary. Neither mode is approved for uploaded or hostile code.
