# Voltesse Dash — authenticated Technician GUI

This branch implements a React/Vite technician interface with a Python/FastAPI API and PostgreSQL. The existing Streamlit branch remains the baseline. The car's driver application (`main.py`, `src/dashboard_gui.py`) is unchanged. The technician uses this GUI on a **laptop**. During development the API and database can also run on that laptop; later the API can read the onboard database over the team's approved network arrangement.

## What works

- Real, provisioned Technician/Admin accounts. No built-in demo password or public signup.
- Argon2id password hashes in the existing `technician_user.password_hash` column.
- Signed JWT in an HttpOnly cookie, 30-minute expiry by default, server-side revocation on logout, and database-persisted sign-in attempt limits.
- CSRF tokens, strict SameSite cookies, request-origin checks, no credentials in browser storage.
- Live, Diagnostics, Sessions, and Settings screens carried over from the Streamlit prototype; an additional manual Backups screen.
- Simulation time slider, optional playback, the same live simulation formulas, temperature chart, configurable warning thresholds.
- Last 20 sessions and five diagnostic chart types. Charts query the project's existing SQL views. Unlike the old fixture curves, these show aggregates of stored telemetry.
- Account-specific settings persisted in PostgreSQL.
- Real `pg_dump` backups with SUCCESS/FAILED audit records and private files on the backend host. Backup success is only reported after `pg_dump` succeeds.

**Hashing protects stored passwords. HTTPS/TLS encrypts communication.** This is not an OAuth provider or third-party SSO integration; it implements local password authentication with JWT sessions. TLS certificates, VPN routing, and the real vehicle connection still require deployment configuration. This is a functional development foundation, not a claim of completed vehicle acceptance testing.

## 1. Prerequisites

- Python 3.11+ (tested with 3.12).
- Node.js 22 LTS or newer compatible with Vite 7; npm.
- PostgreSQL 16+ (or Docker Desktop for the existing database compose file).
- PostgreSQL client tools (`pg_dump`, ideally matching the server major version) on the **API host** for backups. On Windows, PostgreSQL's `bin` directory must be on PATH. Without `pg_dump`, the rest of the app works; manual backups correctly report a failure.

Do not run the project's old SQL demo user seed as your credential-provisioning mechanism. Use the CLI below.

## 2. Check out this branch

From an existing clone:

```powershell
git fetch origin
git switch feature/figma-gui
```

From a new folder:

```powershell
git clone --branch feature/figma-gui https://github.com/Krisdanys/voltesse-dash.git
cd voltesse-dash
```

## 3. Start PostgreSQL

For the existing Docker setup, from the repository root:

```powershell
Copy-Item db/.env.example db/.env
```

Edit `db/.env` and choose a unique `POSTGRES_PASSWORD`. Keep the user/database names consistent with your application connection string. Then:

```powershell
docker compose --env-file db/.env -f db/docker-compose.yml up -d
```

Alternatively use a locally installed PostgreSQL server and an empty development database. Avoid connecting initial testing to the team's only copy of real vehicle data.

## 4. Configure the API and create your real account

From the repository root, Windows PowerShell:

```powershell
cd figma-gui
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edit `figma-gui/.env`:

- Set `AUTH_SECRET` to the generated random value.
- Set `DATABASE_URL` to your actual PostgreSQL connection string. URL-encode special characters in its password.
- Use `TELEMETRY_MODE=SIMULATION` for initial development.
- `COOKIE_SECURE=false` is for localhost HTTP only. For network deployment, configure HTTPS, set `COOKIE_SECURE=true`, and list the exact frontend origin in `ALLOWED_ORIGINS`.

Then, from `figma-gui` with the virtual environment activated:

```powershell
python -m backend.manage migrate
python -m backend.manage create-user --username your.username --name "Your Name" --role ADMIN
python -m backend.manage seed-demo
python -m uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000
```

The account command prompts for a password twice without displaying it (12–1024 characters). There is no default account. `seed-demo` is optional, adds four explicitly marked simulated historical sessions once, and never creates credentials or deletes real sessions.

Leave this terminal running. On macOS/Linux, use `python3 -m venv .venv`, `source .venv/bin/activate`, and `cp .env.example .env`; subsequent Python commands are the same.

## 5. Start the laptop GUI

In a second terminal, from the repository root:

```powershell
npm ci --prefix figma-gui/web
npm run dev --prefix figma-gui/web
```

Open **http://localhost:5173** and sign in with the account you just created. Use the same hostname consistently (localhost vs 127.0.0.1); browser cookies belong to a hostname.

The frontend proxies `/api` to `http://127.0.0.1:8000`. The browser never connects directly to PostgreSQL. `API_PROXY_TARGET` can select another backend address, set only in the dev server's environment. Never expose `DATABASE_URL`, `AUTH_SECRET`, or a `VITE_` variable containing a secret to frontend code.

## 6. Verify the first checkpoint

1. A wrong password is rejected; after five failures the account is limited for 15 minutes.
2. Sign in with the provisioned account. Live displays an explicit SIMULATED label.
3. Move simulation time to 120 seconds. With the original 60 °C default the temperature warning activates. Save a higher threshold in Settings and return to Live to verify it changes the warning.
4. Open Sessions, choose View diagnostics, and confirm all five charts refer to the selected session.
5. Refresh and sign in again if needed; saved settings remain attached to the account.
6. Sign out. Protected `/api/live`, `/api/sessions`, `/api/settings`, `/api/backups`, and diagnostic requests return 401 without a valid session. Replaying a logged-out token also fails.
7. Create a backup. Verify its status and the private dump file on the API host. Do not copy database dumps into the public repository.

## Data modes and existing project integration

`SIMULATION` uses a vendored, unchanged copy of `technician-gui/data/simulator.py` from commit `2739308dca07ad0018fc72499067047bc14db799`. Its live formulas are preserved; added power is an explicitly simulated speed-based approximation. Historical fixtures are persisted into the actual schema and diagnostic charts query the existing views. All generated records are marked SIMULATION / FIGMA DEMO. Development warning defaults are not vehicle-approved safety limits.

`DATABASE` reads the newest non-FIGMA-DEMO entry in `telemetry_log`, polls every two seconds, displays missing values as unavailable, and flags readings older than five seconds. It does not collect CAN itself, claim the CAN bus is healthy, or fall back to fabricated data. The existing driver/backend ingestion remains responsible for writing vehicle readings. Diagnostic data is limited to 2,000 points per chart in this foundation; add deliberate downsampling for longer high-frequency sessions.

This branch's files do not alter `main.py`, any `src/` driver files, `db/schema.sql`, or `feature/technician-gui`. New auth/preferences tables are installed through an additive migration. The existing database schema must be managed with the database engineer before applying changes to a shared deployment.

## Builds and deployment

```powershell
npm run build --prefix figma-gui/web
```

Build output is `figma-gui/web/dist`. For a single-origin deployment, set `WEB_DIST` to its **absolute path** and run the API behind your HTTPS reverse proxy. The frontend remains a technician laptop interface; no technician screen is opened on the car display. Alternatively serve the laptop frontend separately with a same-origin `/api` reverse proxy to the backend. Configure network exposure deliberately; development commands bind to loopback.

Do not expose the unauthenticated driver display as an alternative route to technician data. No driver endpoint is added here.

## Figma Make

See [FIGMA_HANDOFF.md](FIGMA_HANDOFF.md). Connecting the repository is a development/design step, not a database deployment or a VPN setup. No Figma account has been connected by this change.

## Automated checks

```powershell
python -m pip install -r backend/requirements-dev.txt
$env:TEST_DATABASE_URL="postgresql://YOUR_TEST_USER:YOUR_TEST_PASSWORD@localhost:5432/voltesse_test"
python -m pytest -q tests
```

Use a disposable test database. Tests create unique schemas, then remove those schemas; they do not truncate default-schema tables. The suite covers hashes, login failures/limits, protected routes, CSRF, secure cookies, expiration, tampering, logout replay, per-user persistence, diagnostics, unavailable/stale data, and backup failure/success. The native backup test requires `pg_dump` and is skipped if unavailable. A GitHub Actions workflow runs against PostgreSQL 16 and builds the frontend.

Browser checks are in `tests/browser_check.py`: with the API/UI running and an explicitly provisioned throwaway test account, set `UI_BASE_URL`, `UI_TEST_USERNAME`, and `UI_TEST_PASSWORD` in your local environment, install Playwright Chromium, and execute that script. Do not place passwords in command arguments, screenshots, or GitHub configuration files.
