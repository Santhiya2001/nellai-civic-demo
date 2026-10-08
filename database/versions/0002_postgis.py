"""Spatial generated columns and GiST indexes for the PostgreSQL deployment."""

from alembic import op

revision = "0002_postgis"
down_revision = "2fa15b2dc228"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute(
            "ALTER TABLE complaints ADD COLUMN location geography(Point,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude),4326)::geography) STORED"
        )
        op.execute("CREATE INDEX ix_complaints_location_gist ON complaints USING GIST(location)")
        op.execute(
            "ALTER TABLE boundaries ADD COLUMN geom geometry(Geometry,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_GeomFromGeoJSON(geojson::text),4326)) STORED"
        )
        op.execute("CREATE INDEX ix_boundaries_geom_gist ON boundaries USING GIST(geom)")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE complaints DROP COLUMN location")
        op.execute("ALTER TABLE boundaries DROP COLUMN geom")
