"""add scheduling-depth constraints

Revision ID: c4d8e1f7a920
Revises: b7e2a4c19f55
Create Date: 2026-05-30

Adds the data behind richer scheduling:
- subjects.max_periods_per_day  -> subject spacing (default 1 = once/day)
- subjects.requires_double       -> lab/double-period subjects
- teachers.unavailable_slots     -> teacher availability (JSON list)
- pinned_slots table             -> fixed/locked periods the engine honors

All additions are non-destructive: existing rows get sensible server defaults.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d8e1f7a920'
down_revision = 'b7e2a4c19f55'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'max_periods_per_day', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column(
            'requires_double', sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table('teachers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unavailable_slots', sa.JSON(), nullable=True))

    op.create_table(
        'pinned_slots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=True),
        sa.Column('day', sa.String(length=20), nullable=False),
        sa.Column('period_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pinned_slots_organization_id', 'pinned_slots',
                    ['organization_id'], unique=False)

    # Drop the temporary server defaults now that existing rows are backfilled;
    # the application layer supplies these values going forward.
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        batch_op.alter_column('max_periods_per_day', server_default=None)
        batch_op.alter_column('requires_double', server_default=None)


def downgrade():
    op.drop_index('ix_pinned_slots_organization_id', table_name='pinned_slots')
    op.drop_table('pinned_slots')

    with op.batch_alter_table('teachers', schema=None) as batch_op:
        batch_op.drop_column('unavailable_slots')

    with op.batch_alter_table('subjects', schema=None) as batch_op:
        batch_op.drop_column('requires_double')
        batch_op.drop_column('max_periods_per_day')
