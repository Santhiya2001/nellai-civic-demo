# Security policy

This is a local demonstration release. Please report a suspected vulnerability privately to the repository maintainer through GitHub private vulnerability reporting when that feature is configured. Do not include passwords, JWTs, private photos or citizen coordinates in a public issue. A deployment owner must publish a real monitored contact before accepting public users.

Security controls implemented: Argon2 password hashing, signed JWTs, access-token session revocation, rotating refresh tokens, RBAC, private uploads, image decoding/re-encoding, size limits, bounded inputs, audit records, parameterized database access, origin checking for cookie refresh and API rate limits.

The setup script generates secrets. `.env`, `runtime/`, `.venv/`, node modules and signing material are excluded from Git. Never commit the generated demo credentials. The local launcher binds only to 127.0.0.1.

See [docs/security.md](docs/security.md) for the implementation boundaries and future production needs.
