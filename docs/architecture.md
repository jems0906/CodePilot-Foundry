# Architecture

## Boundaries

| Module | Owns | Depends on | Must not do |
| --- | --- | --- | --- |
| `api/tasks.py` | Task CRUD | Database | Read or execute target files |
| `sandbox/` | Local-development policy wrapper and snapshot transfer | OS subprocess or internal runner API | Access the database or call a provider |
| `sandbox_runner/` | Snapshot validation and ephemeral test containers | Docker Engine API | Accept caller-selected commands, mount host paths, or access the database |
| `providers/` | Planning, change proposal, self-review | Provider SDK (optional) | Execute commands, access persistence, or apply changes |
| `agent_service.py` | Synchronous orchestration and temporary snapshot | Tasks, provider, sandbox, recorder | Commit or directly update the target before review |
| `recorder/` | Ordered immutable run events | Database | Modify events after append |
| `review_service.py` | Reviewer decision and guarded patch application | Snapshot, database | Apply rejected/stale proposals |
| `frontend/` | Task submission and human review | HTTP API | Make trust decisions on behalf of the reviewer |

The SQLite schema is used for zero-setup local development and tests. Docker Compose selects PostgreSQL through `DATABASE_URL`; provider choice changes neither schema nor event representation.

## Data flow

1. A human creates a task through `POST /api/tasks`.
2. `POST /api/runs` creates a run and records `run_started`.
3. The selected provider creates a plan and one proposal for the fixed synthetic file `src/text_utils.py`.
4. The backend records the file read and diff, copies the synthetic tree to a temporary directory, applies the proposal there, and sends a tar snapshot to the private runner. The runner validates archive paths/types/size and executes only `pytest -q tests` in a new container with no network, read-only rootfs, non-root UID, dropped capabilities, no-new-privileges, and fixed CPU, memory, PID, and wall-time limits. Local development may select the explicitly weaker subprocess mode.
5. The provider writes a self-review. The run, original hash, proposed content, test result, and immutable events are persisted for review.
6. A reviewer inspects the diff, test output, self-review, and event history. Rejection stores a decision and does not write the target. Approval rechecks the original byte hash and atomically replaces the file; a stale proposal is rejected.

## Critical path and trade-offs

Run execution is synchronous in the API request. This keeps the MVP easy to trace and avoids introducing a queue before there is meaningful load. It blocks a worker for the duration of model and test execution; move orchestration to a durable worker queue before supporting concurrent or long-running production work. API callers should then receive a run ID and poll or subscribe to status.

SQLite keeps local setup simple. Compose exercises PostgreSQL, matching the intended service deployment. Both use the same tables and append-only event rule. Schema migrations are not yet included; add Alembic before evolving production data.

The target remains bundled synthetic code. The runner is a separate internal service; only it mounts the Docker socket, while the API and test container do not. This narrows the execution boundary but still relies on the host Docker daemon and shared kernel. A production service needs a hardened microVM/runtime, a separately protected control plane, stronger sandbox-specific monitoring, and a threat model before accepting hostile code.

## Persistence model

`tasks` stores work requests; `agent_runs` stores provider, state, plan, diff, test outcome, self-review, and proposed content; `code_snapshots` preserves the original and proposed text plus the original hash; `reviews` stores one final human decision; `events` is an ordered append-only stream. Database triggers prevent event updates and deletes. Provider selection is environment-based and does not alter persistence.
