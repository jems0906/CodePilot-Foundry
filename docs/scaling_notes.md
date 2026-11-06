# What Changes at TikTok Scale

This is an honest portfolio MVP, not production AI engineering infrastructure. It has no authentication or tenant model, uses synchronous request execution, stores event payloads in the application database, and can write only one known file in one bundled synthetic repository. SQLite is the local default; Docker Compose uses PostgreSQL. There are no migrations, distributed tracing, provider quotas, or durable queue.

Compose now runs each test command in a disposable, unprivileged container with networking disabled, read-only rootfs, dropped capabilities, and fixed CPU/memory/PID/time bounds. The local development mode still uses a subprocess. The runner control plane mounts the Docker socket, and Docker containers share the host kernel; this is an improved portfolio boundary, not a claim that arbitrary hostile code is safe to execute. The bundled synthetic target remains the only supported input.

At TikTok scale I would:

- Replace the Docker-socket-backed runner with a separately credentialed sandbox control plane and a hardened microVM/runtime; enforce seccomp/AppArmor policy and disk quotas in addition to the current container limits.
- Put orchestration behind a durable queue. Make run steps idempotent and resumable; use cancellation, backpressure, retries, and per-tenant concurrency limits.
- Keep PostgreSQL as the transactional source of truth for tasks, snapshots, and review decisions; evolve it with migrations. Partition or export high-volume event streams to an event/log platform with retention and replay controls.
- Authenticate humans and machine identities, authorize every task/run/review by tenant, audit reviewer actions, and require policy checks for approval.
- Store large diffs and artifacts in encrypted object storage with content hashes, retention policies, and access controls rather than embedding them in event rows.
- Add provider routing, model/tool version pinning, structured-output validation, cost budgets, rate limits, evaluation gates, and privacy review before sending source to any external model.
- Instrument queue time, sandbox startup, command outcomes, test duration, provider errors, approval/rejection rates, and security events without logging secrets or unnecessary source.
- Run a dedicated threat model and red-team the isolation boundary before accepting code from users or agents.

The architectural boundary demonstrated here is the human-reviewable, recorded workflow. The production isolation and operational controls are intentionally not claimed as completed.
