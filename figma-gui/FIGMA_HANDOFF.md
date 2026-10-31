# Figma Make handoff

## Start with the verified local application

Get the API, PostgreSQL, and web UI running using README.md before importing. A Figma connection by itself cannot create the private .env, provision accounts, reach a car's VPN, or run the PostgreSQL database.

## Repository and branch

- Repository: https://github.com/Krisdanys/voltesse-dash
- Branch: `feature/figma-gui`
- Frontend directory: `figma-gui/web`
- Main component: `figma-gui/web/src/App.jsx`
- Styles: `figma-gui/web/src/style.css`
- API: `figma-gui/backend`
- Install: `npm ci --prefix figma-gui/web`
- Dev: `npm run dev` from the repository root (binds to all interfaces for a preview runtime).
- Build: `npm run build`
- Frontend port: 5173. Proxy target: `API_PROXY_TARGET`, default `http://127.0.0.1:8000`.

If your Figma Make account offers **Clone from GitHub**, authorize the repository, select it, and choose `feature/figma-gui` before editing. Configure the preview to run the commands above. Follow Make's prompts for any configuration files its runtime requires. Keep all work on this branch.

Figma's separate **Make in your local codebase** feature is documented as a closed beta with a Mac desktop requirement. Do not assume that workflow is available on a Windows account. Confirm the actual options in your account. If repository cloning is unavailable, the local laptop application still works independently; do not rebuild a fake login to obtain a preview.

A cloud preview's localhost is the cloud runtime, not your laptop or the Pi. Real login requires a reachable backend and PostgreSQL with secrets configured privately in that environment. A private Tailscale/trackside network is not automatically reachable from Figma. Do not make the database public to solve a preview connectivity issue. A preview that cannot reach the API will correctly display a connection/configuration error.

## Suggested first prompt

> Work only on the React technician interface under figma-gui/web in feature/figma-gui. Preserve Live, Diagnostics, Sessions, Settings, Backups, and the existing backend contract. Keep real server authentication and credentials out of frontend code. Do not replace API requests with mock authentication, localStorage tokens, hardcoded accounts, or fake successful backups. Preserve simulation labels, session selection, temperature/battery warning behavior, and unavailable/stale data states. This GUI is used on a technician laptop; the driver's Raspberry Pi screen is a separate application. Refine the interface visually without modifying main.py, src/, or database schema files. Tell me if your preview cannot reach the configured API.

## API contract

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/auth/login` | JSON username/password; sets HttpOnly cookie and returns CSRF token |
| GET | `/api/auth/me` | Current name/role and CSRF token; 401 without authentication |
| POST | `/api/auth/logout` | Revoke session in database and clear cookie |
| GET | `/api/live?t=30` | Labeled simulated or stored telemetry; nullable readings/stale flag |
| GET | `/api/sessions` | Newest 20 sessions |
| GET | `/api/sessions/{id}/diagnostics` | Five chart datasets from SQL views |
| GET/PUT | `/api/settings` | Per-account warning thresholds |
| GET/POST | `/api/backups` | Audit records / actual server-side pg_dump |

For mutations send `X-Requested-With: VoltesseGUI`; authenticated mutations also need `X-CSRF-Token` returned by login or `/auth/me`. Keep cookies and API under one browser origin through the proxy. The frontend intentionally has no bearer token in JavaScript storage.

Official references checked during implementation:
- https://help.figma.com/hc/en-us/articles/44220165255063-Use-Git-with-Figma-Make-and-code-layers
- https://help.figma.com/hc/en-us/articles/40775535020695-Make-in-your-local-codebase
