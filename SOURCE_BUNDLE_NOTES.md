# RoboIQ Guardian — source bundle (not a validated merged application)

- Frontend source copied unchanged from roboiq-guardian_UI.zip (RoboIQ_Guardian/src, public and frontend config).
- Backend Python and data copied unchanged from RoboIQ_Code.zip (RoboIQ_Code/RoboIQ-Guardian/backend, data, tests).
- Existing sources have not been rewritten or contract-adapted.
- UI source currently has four main sections (Fleet, Investigate, Recover, Evidence), not six.
- src/services/api.ts probes /api/arms and /api/events while backend primarily provides /fleet and /incidents; interface adapters remain to be verified.
- Python envs, bytecode, node_modules, environment secrets and caches are excluded. Application data/cache AI JSON is included.
- Both uploaded original ZIPs are unmodified. No claim of full integration/build/deployment testing.

Run frontend from bundle root: npm install ; npm run dev.
Run backend from bundle root: python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8001
For local proxy, set VITE_FASTAPI_URL=http://127.0.0.1:8001 before starting frontend, or configure Vite proxy; adjust for the actual backend route contracts.
