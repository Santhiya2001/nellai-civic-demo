# Neervalam migrations

Initial module tables are included in the frozen initial Alembic revision. Later schema changes require a new Alembic revision under database/versions. Prefix table names with the module name. Never change a released revision. Test both upgrade and downgrade against a disposable PostgreSQL database.
