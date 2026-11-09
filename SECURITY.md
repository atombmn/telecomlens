# Security Policy

TelecomLens processes sensitive data — corporate subscriber numbers, names, and
per-line spend parsed from Safaricom postpay statements. We take its security
seriously and welcome responsible disclosure.

## Supported versions

| Version | Supported |
|---------|-----------|
| 4.3.x   | ✅ Yes (current) |
| 4.2.x and earlier | ⚠️ Please upgrade — see the hardening in 4.3.0 |

## Reporting a vulnerability

**Please report privately — do not open a public issue for security problems.**

Use **GitHub's private vulnerability reporting**:
[**Report a vulnerability**](https://github.com/atombmn/telecomlens/security/advisories/new).
This opens a private advisory visible only to you and the maintainers.

Please include, as far as you can:

- the affected version or commit,
- a description of the issue and its impact,
- steps to reproduce (a proof-of-concept is ideal), and
- any suggested remediation.

We aim to acknowledge a report within **5 working days** and to agree a
disclosure timeline with you. Please give us a reasonable window to ship a fix
before any public disclosure.

## Scope and threat model

TelecomLens is designed as a **single-operator, self-hosted tool bound to
loopback** (`127.0.0.1`). Its security model, and the hardening added in 4.3.0,
are described in [`docs/SECURITY_HARDENING.md`](docs/SECURITY_HARDENING.md).

The following are **in scope**:

- Authentication/authorisation bypass of the app-token control.
- Server-Side Request Forgery via the webhook feature.
- Path traversal / arbitrary file access via folder import.
- Cross-site request forgery against the local API, or any way for a web page
  the operator merely visits to read data or take actions.
- Stored or reflected XSS in the dashboard.
- Injection (SQL, command) or deserialisation flaws.

The following are **out of scope** / known accepted risks:

- Attacks that require the operator to have deliberately widened exposure
  (e.g. binding to `0.0.0.0`, setting `CORS_ORIGINS=*`, or
  `WEBHOOK_ALLOW_PRIVATE=true`) **against the documented guidance**. Please still
  tell us if the default guidance itself is unsafe.
- A local user who already has full access to the operator's account and
  filesystem (the data is on their disk by design).
- Denial of service from a trusted local operator.

## Handling of sensitive data

- Databases (`*.db`), uploaded PDFs (`bills/*.pdf`), the environment file
  (`.env`), and the generated token (`.telecomlens_secret`) are git-ignored and
  must never be committed.
- Please do not include real subscriber data in bug reports — synthetic
  examples are enough to reproduce.
