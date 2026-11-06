# CodePilot Foundry

**A workspace where an AI coding agent helps humans improve a real codebase, with every agent action running in a sandbox, recorded, and traceable.**

CodePilot Foundry is a local-first portfolio MVP. It operates only on the bundled synthetic Python project. The default mock provider is deterministic and needs no API key. Proposed changes are tested on a disposable snapshot and never touch the target until a reviewer approves them.

## Start locally

Requires Python 3.11+, Node.js 20+, and npm. In PowerShell, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pip install -r target_codebase\requirements.txt
```

Start the API in one terminal:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

Start the UI in another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open <http://localhost:5173>. This standalone development mode uses a local subprocess executor and is only for the bundled synthetic code. The API health check is at <http://localhost:8000/api/health>, and the interactive API reference is at <http://localhost:8000/docs>.

To use PostgreSQL and per-run container isolation, run `docker compose up --build` and open <http://localhost:8080>. Compose stores PostgreSQL data in a named volume; the API image contains the bundled synthetic target and does not mount the host checkout. Each run is sent to the private sandbox runner, which starts a disposable test container with no network, a read-only root filesystem, a non-root UID, dropped capabilities, and CPU, memory, PID, and time limits.

EvalForge is the companion benchmark dashboard. With Compose running, open <http://localhost:8081>; its API is at <http://localhost:8001/docs>. It reads saved CodePilot runs from the internal API, evaluates them against generated scenarios, and persists score snapshots separately. The local development UI is available at <http://localhost:5174> when started from `evalforge/frontend`.

## Use the workspace

Create a task in the left panel and run it. The mock provider proposes a Unicode case-folding fix, tests it on a temporary copy, and records the plan, file read, diff, command output, and self-review. Inspect the event history and diff, then reject or approve. Rejection leaves the target bytes unchanged; approval applies the saved proposal only if the original file still matches its snapshot.

The included target starts with intentionally failing tests. Running them directly before an agent proposal should show the seeded Unicode normalization failure:

```powershell
cd target_codebase
python -m pytest -q
```

## Optional OpenAI provider

Install `backend/requirements-openai.txt`, set `AGENT_PROVIDER=openai` and `OPENAI_API_KEY` in the backend process environment, then restart the API. `OPENAI_MODEL` optionally selects a model. Responses are constrained by JSON Schema; the provider cannot select or invoke commands. The backend still runs only its fixed test command on the synthetic snapshot.

## Checks

```powershell
cd backend
python -m pytest tests -q
cd ..\frontend
npm ci
npm run build
```

To run the same container-level acceptance gate used in CI, start Docker Compose and run the smoke script from the repository root:

```powershell
docker compose up --build -d
python scripts\sandbox_smoke.py
docker compose down
```

## Security boundary

The standalone local development mode uses `shell=False`, an executable allowlist, command-specific restrictions, workspace containment, a filtered child environment, and output redaction, but it does not isolate a process from the host. Compose runs tests in a per-run container with network disabled and resource restrictions. Only the internal `sandbox-runner` service mounts the Docker Engine socket; the CodePilot API and test container do not. Docker containers still share the host kernel, and compromise of the runner control plane or Docker daemon remains a high-impact risk. Do not point either mode at uploaded or otherwise untrusted code; use a hardened microVM/runtime and a separately protected container-control service before production use.

## Project map

- `backend/app`: API, providers, sandbox, recorder, and review flow.
- `backend/tests`: policy, timeout, redaction, event immutability, and end-to-end gates.
- `sandbox_runner`: private Docker control plane and per-run container policy.
- `frontend`: React/Vite review workspace.
- `target_codebase`: synthetic source and deliberately failing tests.
- `docs`: architecture, runbooks, worked example, and scale limitations.
- `docker-compose.yml`: PostgreSQL-backed deployment with an internal sandbox network.
- `evalforge`: deterministic benchmark API and dashboard for CodePilot run quality.
