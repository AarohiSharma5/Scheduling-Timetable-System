"""add teacher preferences (soft constraints + workload targets)

Revision ID: e2c7a9114f08
Revises: d9f3b6e2a14c
Create Date: 2026-05-31

Adds a teacher_preferences table (one row per teacher) holding optional soft
scheduling preferences: preferred classes/subjects/periods, extra blocked slots,
soft daily/weekly workload targets, and charge-acceptance flags.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2c7a9114f08'
down_revision = 'd9f3b6e2a14c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'teacher_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('preferred_classes', sa.JSON(), nullable=True),
        sa.Column('preferred_subjects', sa.JSON(), nullable=True),
        sa.Column('preferred_slots', sa.JSON(), nullable=True),
        sa.Column('blocked_slots', sa.JSON(), nullable=True),
        sa.Column('max_periods_day', sa.Integer(), nullable=True),
        sa.Column('max_periods_week', sa.Integer(), nullable=True),
        sa.Column('allow_class_teacher_charge', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('allow_extra_charge', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('teacher_id'),
    )
    op.create_index('ix_teacher_preferences_organization_id', 'teacher_preferences',
                    ['organization_id'], unique=False)
    op.create_index('ix_teacher_preferences_teacher_id', 'teacher_preferences',
                    ['teacher_id'], unique=False)

    # Drop temporary server defaults; the app layer sets these going forward.
    with op.batch_alter_table('teacher_preferences', schema=None) as batch_op:
        batch_op.alter_column('allow_class_teacher_charge', server_default=None)
        batch_op.alter_column('allow_extra_charge', server_default=None)


def downgrade():
    op.drop_index('ix_teacher_preferences_teacher_id', table_name='teacher_preferences')
    op.drop_index('ix_teacher_preferences_organization_id', table_name='teacher_preferences')
    op.drop_table('teacher_preferences')
