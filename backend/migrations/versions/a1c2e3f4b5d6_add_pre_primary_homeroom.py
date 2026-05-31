"""pre-primary homeroom scheduling

Revision ID: a1c2e3f4b5d6
Revises: f0a1b2c3d4e5
Create Date: 2026-06-01

Adds:
  * batches.homeroom_teacher_id          - primary homeroom teacher (pre-primary)
  * school_config.pre_primary_mode       - "single" | "specialist"
  * school_config.pre_primary_support_subjects - JSON list of specialist subjects
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c2e3f4b5d6'
down_revision = 'f0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('batches', sa.Column('homeroom_teacher_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_batches_homeroom_teacher', 'batches', 'teachers',
        ['homeroom_teacher_id'], ['id'],
    )
    op.add_column('school_config', sa.Column(
        'pre_primary_mode', sa.String(length=20), nullable=False,
        server_default='single',
    ))
    op.add_column('school_config', sa.Column(
        'pre_primary_support_subjects', sa.JSON(), nullable=True,
    ))


def downgrade():
    op.drop_column('school_config', 'pre_primary_support_subjects')
    op.drop_column('school_config', 'pre_primary_mode')
    op.drop_constraint('fk_batches_homeroom_teacher', 'batches', type_='foreignkey')
    op.drop_column('batches', 'homeroom_teacher_id')
