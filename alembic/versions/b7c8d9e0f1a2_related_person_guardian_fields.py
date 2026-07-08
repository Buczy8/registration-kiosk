"""Add guardian-specific fields to related persons."""

from alembic import op
import sqlalchemy as sa


revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "related_persons",
        sa.Column("guardian_relation", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "related_persons",
        sa.Column(
            "image_publication_consent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "related_persons",
        sa.Column("vehicle_type", sa.String(length=14), nullable=True),
    )
    op.add_column(
        "related_persons",
        sa.Column("vehicle_model", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "related_persons",
        sa.Column("vehicle_registration_number", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("related_persons", "vehicle_registration_number")
    op.drop_column("related_persons", "vehicle_model")
    op.drop_column("related_persons", "vehicle_type")
    op.drop_column("related_persons", "image_publication_consent")
    op.drop_column("related_persons", "guardian_relation")
