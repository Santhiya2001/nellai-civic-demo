# Testing

Run backend tests in SQLite isolation with `.venv/bin/python -m pytest`. Each test gets a disposable schema; test credentials and images are generated. This covers the complete complaint lifecycle, working-day holidays, escalation idempotence, unauthorized access, upload validation, refresh replay, account deletion, duplicates, module disablement, land-verification constraints, activity capacity and the disabled AI contract.

`scripts/test_postgis.py` creates a uniquely named temporary PostgreSQL database using the local database account, applies actual migrations, checks the two GiST indexes, runs the suite, and removes only that temporary database. The existing demo database is not reset. The database user needs permission to create/drop this disposable test database.

The web build is type checked using `npm --prefix web run build`. Browser tests require the running demo, generated `runtime/demo-credentials.json`, and Chrome at `/usr/bin/google-chrome` (override with `CHROME_PATH`). Run:

```bash
cd web
npm run test:e2e
```

Tests create a clearly labelled demonstration report and complete its workflow. They also check environmental and admin screens, capture presentation screenshots and verify the responsive layout. Output is stored in `runtime/browser-report` and `presentation/screenshots`.

The email-preview browser scenario uses the prepared complaint saved by
`.venv/bin/python scripts/test_complaint_email.py`. This helper submits one labelled
test on its first run and reuses it later. It is a local demo action, not a unit test.
Set `SCREENSHOT_DIR` when running Playwright to use a different screenshot folder;
the current presentation uses `presentation/demo-ready/screenshots`.

These checks are functional verification, not a large-scale performance evaluation. Do not invent classification accuracy, response-time improvements or live deployment statistics in a presentation. The final test evidence is recorded in `docs/verification.md`.
