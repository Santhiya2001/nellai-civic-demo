# Security and privacy implementation notes

## Implemented

- Passwords use Argon2; passwords and secrets are not returned in account APIs or audit details.
- JWT algorithm, issuer, audience, expiry and token type are validated. Access requests also check the database session and current user role.
- Refresh-token rotation uses an atomic digest match. Detected reuse revokes that session.
- The browser keeps access tokens in memory. HttpOnly/SameSite refresh cookies use secure transport in production mode, and cookie operations require a trusted Origin.
- Public APIs omit user identity, contact data, complaint descriptions and photo IDs. Map coordinates are rounded to three decimals; exact coordinates require complaint access.
- Uploaded images must decode as JPEG/PNG/WebP, stay within size/dimension bounds, and are re-encoded without EXIF metadata. Photos are fetched through authenticated routes rather than a public static directory.
- Authority permissions depend on the assigned authority ID. Citizens cannot choose privileged roles during registration. Only a super administrator can grant staff roles.
- Workflow changes, assignments, module toggles and relevant record changes write audit rows.
- Local rate limits use process memory. A configured Redis store provides shared counters; production-mode validation requires Redis.

## Demo boundaries

This has not received an independent security audit. The local demo is not configured for anonymous internet traffic. HTTP is used only on localhost. Browser pages poll the API rather than using push delivery.

Authentication identifies an email or phone with a password; contact verification, recovery, staff MFA, bot controls and a password reset process are not implemented. The demo does not promise production-grade anti-abuse protection.

PostgreSQL/file backups, strict reverse-proxy request limits, TLS, log collection, secret rotation, monitoring, data lifecycle jobs and tested disaster recovery must be configured before a public service. SMTP is optional and requires real settings. Notification email is an at-least-once outbox: a crash after sending but before committing could duplicate a message.

Publicly rounding locations reduces precision; it does not provide a mathematical anonymity guarantee. Do not upload sensitive photographs or personal data in this demo. Official boundaries and land ownership require confirmed records, never imagery-derived assumptions.

Account deletion disables sign-in, removes contact information, removes the reporting account's original complaint photos/text and anonymizes report ownership. Audit/history and other operational records are retained in this demo; a complete deletion/retention policy needs operator review before public deployment. `RETENTION_DAYS` is a documented policy setting only; no unattended purge job is included.
