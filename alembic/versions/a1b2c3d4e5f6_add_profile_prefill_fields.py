"""Add profile prefill fields for full autofill."""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "741d4280a258"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("pesel", sa.String(length=11), nullable=True))
    op.add_column(
        "user_profiles", sa.Column("id_card_series", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "user_profiles", sa.Column("id_card_number", sa.String(length=30), nullable=True)
    )
    op.add_column(
        "user_profiles",
        sa.Column("last_participant_role", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "user_profiles", sa.Column("last_vehicle_type", sa.String(length=30), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "last_vehicle_type")
    op.drop_column("user_profiles", "last_participant_role")
    op.drop_column("user_profiles", "id_card_number")
    op.drop_column("user_profiles", "id_card_series")
    op.drop_column("user_profiles", "pesel")
