"""Add vehicle brand to related persons."""

from alembic import op
import sqlalchemy as sa


revision = "c2d3e4f5a6b7"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "related_persons",
        sa.Column("vehicle_brand", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("related_persons", "vehicle_brand")
