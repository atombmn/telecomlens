# TelecomLens — Security Hardening (v4.3.0)

This document describes TelecomLens's security model and the controls added in
**v4.3.0** in response to the purple-team audit of v4.2.0. It is the reference
for operators deploying the tool and for anyone reviewing its security.

## Threat model in one paragraph

TelecomLens is a **single-operator, self-hosted** analytics tool that holds
sensitive telco data (subscriber MSISDNs, names, per-line spend). It is meant to
run bound to **loopback** (`127.0.0.1:8000`) on one trusted workstation. The key
insight from the audit is that *loopback is not a trust boundary on its own*: the
operator's **browser** bridges onto the local API, so any web page they visit
could script `localhost` unless the app defends itself. v4.3.0 makes the app
**safe by default** rather than safe by assumption.

## Controls added in 4.3.0

| # | Control | What it stops | Config |
|---|---------|---------------|--------|
| 1 | **App token on every state-changing request** (`X-TL-Token`) | A cross-origin page (or any non-dashboard caller) forging POST/PUT/PATCH/DELETE — webhook registration, retags, shutdown | `AUTH_ENABLED`, `APP_TOKEN` |
| 2 | **Strict CORS** (same-origin by default) | A malicious site *reading* API responses (bill data) in the operator's browser | `CORS_ORIGINS` |
| 3 | **Host-header allow-list** | DNS-rebinding attacks against loopback | `TRUSTED_HOSTS` |
| 4 | **Webhook SSRF guard** | Webhooks pointed at `169.254.169.254`, `127.0.0.1`, or private ranges; exfiltration/probing of internal services | `WEBHOOK_ALLOW_HTTP`, `WEBHOOK_ALLOW_PRIVATE` |
| 5 | **Folder-import confinement** | Reading arbitrary server directories via `import-folder` | `IMPORT_BASE` / `BILLS_FOLDER` |
| 6 | **Upload size + type caps** | Memory-exhaustion from huge/endless uploads; non-PDF payloads | `MAX_UPLOAD_MB` |
| 7 | **Security headers + CSP** | Clickjacking, MIME-sniffing, external resource injection; vendored Chart.js removes the CDN dependency | `SECURITY_HEADERS` |
| 8 | **Generic error messages** | Filesystem/toolchain detail leaking to clients | — |
| 9 | **Inspector-based schema introspection** | Removes an f-string-SQL footgun (`PRAGMA`) | — |
| 10 | **Bounded dependencies + Dependabot** | Supply-chain drift / malicious major releases | `requirements.txt`, `.github/dependabot.yml` |

## How the app token works

- On first run (with `AUTH_ENABLED=true`, the default), TelecomLens generates a
  random token and stores it in **`.telecomlens_secret`** (git-ignored,
  `chmod 600`). Set `APP_TOKEN` explicitly to pin a known value.
- The dashboard is served from the same origin, and the token is injected into
  the page as a `<meta name="tl-token">`. Because the **same-origin policy**
  stops any other web origin from reading that HTML, a malicious page cannot
  learn the token — so it cannot forge state-changing calls.
- **Read** endpoints (`GET`) are not token-gated; cross-origin *reading* is
  blocked by CORS instead, and a local non-browser reader is out of the
  documented threat model.
- **Driving the API from your own scripts:** send the token in the header, e.g.

  ```bash
  TOKEN=$(cat .telecomlens_secret)
  curl -X POST http://127.0.0.1:8000/api/bills/import-folder \
       -H "X-TL-Token: $TOKEN" -H "Content-Type: application/json" \
       -d '{"folder":"bills"}'
  ```

## Deployment guidance

**Default (recommended): single machine, loopback.**
Run as the start scripts do — `uvicorn main:app --port 8000` (binds
`127.0.0.1`). Leave all security settings at their defaults. Nothing else is
required; the token is handled automatically.

**Shared / LAN install (advanced).** If you must expose TelecomLens beyond
loopback:

1. Put it behind a reverse proxy that terminates TLS and adds real
   authentication (SSO or basic-auth). Do **not** expose the raw port.
2. Add the host to `TRUSTED_HOSTS` (e.g. `TRUSTED_HOSTS=telecom.internal`).
3. Set `CORS_ORIGINS` only if a *different* web origin must call the API.
4. Keep `AUTH_ENABLED=true` and set a strong explicit `APP_TOKEN`.
5. Never set `CORS_ORIGINS=*` or `WEBHOOK_ALLOW_PRIVATE=true` unless you fully
   understand the consequences.

## Content-Security-Policy

The emitted policy is:

```
default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self';
object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

`'unsafe-inline'` is required for scripts because the single-file SPA uses inline
event handlers; it is a known, accepted limitation. The policy still blocks
external script/style/frame loads, clickjacking (`frame-ancestors 'none'`),
plugin content (`object-src 'none'`), and base-tag hijacking, and confines
network calls to the same origin. Chart.js is vendored locally
(`static/chart.umd.min.js`) so the app needs no third-party CDN and works
offline.

## Dependencies

`requirements.txt` uses **bounded ranges** (`>=min,<next-major`) so installs stay
within a tested major line and cannot silently jump to a breaking or malicious
new major.

For a fully pinned, **hash-verified** install, generate a lock for *your*
platform (a lock is platform- and interpreter-specific, so it is generated
locally rather than shipped):

```bash
pip install pip-tools
pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
pip install -r requirements.lock
```

Dependabot (`.github/dependabot.yml`) opens weekly update PRs and flags known
vulnerabilities.

## Residual risks (accepted)

- A **local** process or user on the same machine can read the SQLite DB and the
  token file directly. This is inherent to a single-user local tool; protect the
  workstation.
- `'unsafe-inline'` scripts (see CSP above). Output is consistently
  HTML-escaped in the SPA, so stored XSS was not found; the CSP is
  defence-in-depth, not the primary control.
- These are documented, not latent — see `SECURITY.md` for what remains in scope
  for reports.
