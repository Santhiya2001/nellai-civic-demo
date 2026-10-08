"""Durable outgoing authority alerts for new complaints."""

from alembic import op
import sqlalchemy as sa

revision = "0003_complaint_emails"
down_revision = "0002_postgis"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "complaint_emails",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("complaint_id", sa.String(36), sa.ForeignKey("complaints.id"), nullable=False),
        sa.Column("recipient", sa.String(254), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("complaint_id", "recipient", name="uq_complaint_email_recipient"),
    )
    op.create_index("ix_complaint_emails_pending", "complaint_emails", ["state", "next_attempt_at"])


def downgrade():
    op.drop_table("complaint_emails")
