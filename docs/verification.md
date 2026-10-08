# Verification record — 8 October 2026

## Portable ZIP verification — 7–8 October 2026

- Extracted the ZIP into a separate folder whose path contains spaces. Verified
  every file against the included SHA-256 manifest and checked ZIP integrity.
- First setup created a fresh Python environment, downloaded dependencies,
  applied SQLite migrations and generated new demo records and private logins.
  No original `.env`, database, uploads or credentials were copied.
- **25/25 backend/module tests passed** on the extracted SQLite installation.
  **3/3 browser scenarios passed** against that separate app: the complete
  complaint lifecycle, administration/modules/responsive layout, and the outbox.
- Public-page/API checks and all three role logins passed. A labelled test
  complaint queued an alert while SMTP remained disconnected; no portable-copy
  test email was sent.
- The Linux launcher repeated setup successfully after a clean shutdown and
  preserved all 14 seeded/test complaints and generated login credentials.
- Python 3.12 binary dependency resolution passed for Windows x64, macOS 14+
  Intel and macOS 11+ Apple Silicon. Intel Macs use a platform-specific Argon2
  binding; Windows omits uvloop and includes colorama.
- Native Windows/macOS application execution was not available on this Linux
  host. Dependency checks and launcher review do not claim native end-to-end tests.
- Updated 23-slide PPT and matching 23-page PDF were regenerated. The modified
  email and portable-deployment slides were rendered and visually checked.
- The release excludes private settings, runtime data, environment folders,
  node_modules, caches and the superseded presentation. Known local credential
  values are checked against packaged file contents before writing the archive.

## Gmail connection check — 7 October 2026

- The saved sender and recipient match `sandymuthukutti@gmail.com`, and the
  application reads the saved 16-character App Password correctly.
- After a new App Password was configured, Gmail accepted test complaint
  **NGC-063524AD** at **14:52:32 UTC on 7 October 2026**. Its persisted state is
  **SENT**. This establishes SMTP acceptance, not confirmed Inbox/Spam arrival.
- The app and worker were restarted with the verified settings. The other queued
  complaint alert was also sent automatically: **2 SENT, 0 PENDING, 0 FAILED**.
  Seed-user notifications addressed to `.example` were skipped in demo mode.
- The local smoke check passed again, including public pages, configuration,
  maps, modules, and login/records/logout for all three demo roles.
- The browser email-outbox scenario passed again after delivery, including the
  complaint link through sign-in. Its screenshot now shows the real SENT state.
- **25/25 backend/module tests passed** on disposable PostgreSQL/PostGIS on
  7 October, with zero failures/errors/skips. These tests use mocked SMTP.
- The 23-slide PPT/PDF and speaking guide now distinguish original-PC SMTP
  verification from the private email setup required on another PC.

## Demo preparation — 6 October 2026

- **23/23 backend and module tests passed** on a disposable PostgreSQL/PostGIS
  database. All migrations, including the complaint email outbox, and both spatial
  indexes were checked. The disposable test database was removed.
- **3/3 Playwright browser scenarios passed**: complete complaint resolution and
  citizen verification; admin/environmental screens and responsive layout; and the
  authority email preview with a complaint link preserved through sign-in.
- **Production React/TypeScript build passed** and **Python lint passed**.
- Email tests verify queued alerts for assigned and unassigned complaints,
  recipient selection, message content, delayed retries, failed-attempt limits,
  disabled SMTP and administrator-only previews. All test SMTP delivery is mocked.
- The prepared test complaint is **NGC-063524AD**, addressed to
  `sandymuthukutti@gmail.com`. Its real database email state is **PENDING**, with
  no delivery attempts. The Gmail sending account remains unconfigured.
- The missing PostGIS container was restored using the existing named data volume.
  Existing demo records were retained. The localhost app is available on port 8080
  while its launcher and database are running.
- The current 23-slide PowerPoint and PDF are in `presentation/demo-ready/`.
  Screenshots were captured from the running updated app; slide notes are included.

At that earlier point no real Gmail delivery had been verified. The successful
7 October SMTP test is recorded above. No trained AI evaluation or government
integration is claimed.

## Earlier verification — 19 September 2026

## Passed

- **15/15 backend and module tests** on a fresh disposable PostgreSQL/PostGIS database. Actual Alembic migrations and both spatial GiST indexes were checked before the tests. The disposable database was removed; demo data was retained.
- **2/2 Playwright browser scenarios** in Google Chrome: photo submission → authority acknowledgement/work/resolution → citizen verification; and administrator/environmental screens plus a 390-pixel responsive layout.
- **React TypeScript check and production web build** through `npm run build`.
- **Python lint** through `ruff check`.
- **Five module packages validated** and **45 OpenAPI paths exported**.
- An earlier SQLite run also passed the same 15 backend/module tests.

Browser tests created a labelled test complaint and captured actual screenshots in `presentation/screenshots/`. The PostgreSQL JUnit report is kept privately at `runtime/test-results-postgis.xml`. The browser HTML report is in `runtime/browser-report/`.

The test libraries emit two upstream deprecation warnings about Starlette/httpx and an AnyIO alias. Tests passed; these warnings are not application errors.

## Scope limits

This is functional local verification. No AI model evaluation, real government integration, mobile release, store submission, public deployment, production load test or independent security audit was performed. The optional Docker Compose recipe is provided; the prepared environment uses the tested local launcher and a dedicated PostGIS container.
