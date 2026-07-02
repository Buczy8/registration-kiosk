"""initial schema"""

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql

revision = "f0f4afe3dfd9"
down_revision = None
branch_labels = None
depends_on = None

NEXT_START_NUMBER_FUNCTION = """
CREATE OR REPLACE FUNCTION next_start_number(p_sequence_date DATE)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_next INT;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('start_number:' || p_sequence_date::TEXT));

    SELECT COALESCE(MAX(start_number), 0) + 1
    INTO v_next
    FROM submissions
    WHERE sequence_date = p_sequence_date;

    RETURN v_next;
END;
$$;
"""


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.create_table('forms',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('version', sa.String(length=20), nullable=False),
    sa.Column('schema_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('pdf_template_path', sa.Text(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_index('uq_forms_one_active', 'forms', ['is_active'], unique=True, postgresql_where=sa.text('is_active = TRUE'))
    op.create_table('users',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=True),
    sa.Column('last_name', sa.String(length=100), nullable=True),
    sa.Column('phone', sa.String(length=30), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('failed_login_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'], unique=False)
    op.create_table('related_persons',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('owner_user_id', sa.UUID(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_related_persons_owner_user_id', 'related_persons', ['owner_user_id'], unique=False)
    op.create_table('user_profiles',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('document_number', sa.String(length=50), nullable=True),
    sa.Column('ice_name', sa.String(length=150), nullable=True),
    sa.Column('ice_phone', sa.String(length=30), nullable=True),
    sa.Column('vehicles_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('submissions',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('form_id', sa.UUID(), nullable=False),
    sa.Column('form_version', sa.String(length=20), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('filled_for_related_person_id', sa.UUID(), nullable=True),
    sa.Column('mode', sa.Enum('guest', 'account', name='submission_mode'), nullable=False),
    sa.Column('participant_role', sa.Enum('driver', 'passenger', 'legal_guardian', name='participant_role'), nullable=False),
    sa.Column('vehicle_type', sa.Enum('car', 'motorcycle', 'gokart', name='vehicle_type'), nullable=False),
    sa.Column('start_number', sa.Integer(), nullable=False),
    sa.Column('sequence_date', sa.Date(), nullable=False),
    sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('consents_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('declarations_accepted', sa.Boolean(), nullable=False),
    sa.Column('signature_path', sa.Text(), nullable=True),
    sa.Column('signature_hash', sa.String(length=128), nullable=True),
    sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('pdf_path', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('submitted', 'print_queued', 'print_done', 'print_failed', name='submission_status'), server_default=sa.text("'submitted'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(mode = 'guest' AND user_id IS NULL AND filled_for_related_person_id IS NULL) OR (mode = 'account' AND user_id IS NOT NULL)", name='chk_submissions_account_requires_user'),
    sa.CheckConstraint("filled_for_related_person_id IS NULL OR mode = 'account'", name='chk_submissions_related_person_requires_account'),
    sa.ForeignKeyConstraint(['filled_for_related_person_id'], ['related_persons.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sequence_date', 'start_number', name='uq_submissions_sequence_date_start_number')
    )
    op.create_index('idx_submissions_created_at', 'submissions', ['created_at'], unique=False)
    op.create_index('idx_submissions_filled_for_related_person_id', 'submissions', ['filled_for_related_person_id'], unique=False)
    op.create_index('idx_submissions_sequence_date', 'submissions', ['sequence_date'], unique=False)
    op.create_index('idx_submissions_status', 'submissions', ['status'], unique=False)
    op.create_index('idx_submissions_user_id', 'submissions', ['user_id'], unique=False)
    op.create_table('print_jobs',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('submission_id', sa.UUID(), nullable=False),
    sa.Column('copies', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.Enum('queued', 'printing', 'done', 'failed', name='print_job_status'), server_default=sa.text("'queued'"), nullable=False),
    sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('idempotency_key', sa.String(length=100), nullable=True),
    sa.Column('queued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('idx_print_jobs_status', 'print_jobs', ['status'], unique=False)
    op.create_index("idx_print_jobs_submission_id", "print_jobs", ["submission_id"], unique=False)
    op.execute(NEXT_START_NUMBER_FUNCTION)


def downgrade() -> None:
    op.drop_index('idx_print_jobs_submission_id', table_name='print_jobs')
    op.drop_index('idx_print_jobs_status', table_name='print_jobs')
    op.drop_table('print_jobs')
    op.drop_index('idx_submissions_user_id', table_name='submissions')
    op.drop_index('idx_submissions_status', table_name='submissions')
    op.drop_index('idx_submissions_sequence_date', table_name='submissions')
    op.drop_index('idx_submissions_filled_for_related_person_id', table_name='submissions')
    op.drop_index('idx_submissions_created_at', table_name='submissions')
    op.drop_table('submissions')
    op.drop_table('user_profiles')
    op.drop_index('idx_related_persons_owner_user_id', table_name='related_persons')
    op.drop_table('related_persons')
    op.drop_index('idx_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_table('users')
    op.drop_index("uq_forms_one_active", table_name="forms", postgresql_where=sa.text("is_active = TRUE"))
    op.drop_table("forms")

    op.execute("DROP FUNCTION IF EXISTS next_start_number(DATE)")

    op.execute("DROP TYPE IF EXISTS print_job_status")
    op.execute("DROP TYPE IF EXISTS submission_status")
    op.execute("DROP TYPE IF EXISTS vehicle_type")
    op.execute("DROP TYPE IF EXISTS participant_role")
    op.execute("DROP TYPE IF EXISTS submission_mode")
