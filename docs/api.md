# API guide

The live OpenAPI documentation is at `/docs` and `/redoc`; the machine-readable contract is `/openapi.json`. The saved snapshot is `docs/openapi.json`. Route schemas and example field types come from Pydantic models. API routes use `/api/v1`.

## Authentication

1. `POST /api/v1/auth/register` with `name`, `email` or international `phone`, and a password of at least 12 characters. Registration always creates a citizen.
2. `POST /api/v1/auth/login` with `identifier` and `password`. It returns an access token, refresh token and own-user profile, and sets an HttpOnly refresh cookie for the web client.
3. Send `Authorization: Bearer <access_token>` on protected calls.
4. `POST /api/v1/auth/refresh` rotates the refresh token. API clients provide `refresh_token` in JSON; web cookie requests need a configured trusted Origin. Reusing an old refresh token revokes its session.
5. `POST /api/v1/auth/logout` revokes the refresh session. Existing access tokens for that session stop working.

The demo has password authentication for email/mobile identifiers. Contact ownership verification and password recovery by email/SMS are not implemented.

## Main APIs

| Method | Route | Purpose / access |
|---|---|---|
| POST | `/uploads` | Re-encoded private photo; authenticated owner |
| GET | `/uploads/{id}` | Owner, permitted complaint participant, or administrator |
| POST | `/complaints` | Report with title, description, category, photo ID, coordinates |
| GET | `/complaints` | Own reports, assigned-team reports or all for administrator |
| GET | `/complaints/{id}` | Authorized detail and timeline |
| GET | `/complaints/nearby` | Rounded public summary within a radius |
| POST | `/complaints/{id}/assign` | Administrator assigns a team and calendar |
| POST | `/complaints/{id}/status` | Permitted workflow transition |
| POST | `/complaints/{id}/classify` | Administrator's human category/severity correction |
| POST | `/complaints/{id}/resolve` | Assigned team/admin; photograph and location required |
| POST | `/complaints/{id}/verify` | Reporting citizen confirms or reopens |
| GET / POST | `/complaints/{id}/duplicates`, `/merge` | Administrator review and linking |
| GET | `/map`, `/boundaries`, `/boundaries/lookup` | Public limited GIS data |
| POST | `/authorities`, `/calendars`, `/responsibilities` | Administrator configuration |
| PUT | `/responsibilities/{id}` | Update configuration for future assignments |
| POST | `/escalations/run` | Administrator triggers checks for actually due records |
| GET | `/dashboard`, `/notifications` | Role-filtered metrics and own notifications |
| POST | `/notifications/{id}/read` | Owner marks a notification as read |
| GET / POST | `/trees`, `/planting-sites` | Optional Green Nellai module |
| POST | `/volunteers` | Create/update own volunteer profile |
| GET / POST | `/activities`, `/activities/{id}/join` | Activities and capacity-limited participation |
| GET / POST | `/water-bodies`, `/water-bodies/{id}/observations` | Water module |
| GET / POST | `/modules` | List installed modules / administrator toggle |
| DELETE | `/auth/me` | Password-confirmed deletion of own citizen account |

Routes in the table are relative to `/api/v1`. Lists are capped and some support `limit`/`offset`. Check the OpenAPI schema for exact parameters.

## Errors

401: missing/expired session. 403: insufficient permissions. 404: missing or inaccessible resource. 409: invalid workflow transition, concurrent update or conflicting record. 413: upload/request too large. 415: unsupported or invalid image. 422: invalid fields. 429: rate limit.

Timestamps are serialized as UTC with `Z`; calendar calculations use the configured local time zone. Coordinates use latitude/longitude in WGS84. Radius values are metres.
