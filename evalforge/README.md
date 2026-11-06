# EvalForge

EvalForge is CodePilot Foundry's companion benchmark dashboard. It evaluates saved agent runs against deterministic, generated scenarios and keeps its score snapshots separate from CodePilot's task and review records.

## Run with Docker Compose

From the repository root:

```powershell
docker compose up --build
```

Open <http://localhost:8081>. The API and interactive docs are at <http://localhost:8001/docs>. EvalForge calls CodePilot over the Compose network (`http://backend:8000`) and stores results in its own named volume.

## Run locally

Install `evalforge/backend/requirements.txt`, then start its API from the repository root:

```powershell
python -m uvicorn app.main:app --app-dir evalforge/backend --host 127.0.0.1 --port 8001
```

Start the UI in a second terminal:

```powershell
cd evalforge/frontend
npm ci
npm run dev
```

The Vite port is configured as 5174 and proxies `/api` to 8001. The backend reads CodePilot from `CODEPILOT_API_URL`, defaulting to `http://localhost:8000`.

## Evaluate a run

Select a completed CodePilot run and evaluate it against `unicode-normalization` or one of four generated probes: failed tests, unrelated regression, command-policy violation, or incomplete trace. Each probe mutates only an in-memory copy to verify the evaluator detects that condition; it never alters CodePilot's stored run or events. The dashboard labels probe results separately. Results are idempotent per run and scenario.

Run backend tests from `evalforge/backend` with `python -m pytest tests -q`; build the UI with `npm ci` and `npm run build` from `evalforge/frontend`.
