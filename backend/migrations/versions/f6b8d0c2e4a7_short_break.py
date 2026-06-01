"""short break (fruit break) modeled like lunch

Revision ID: f6b8d0c2e4a7
Revises: e5a7c9b1d3f6
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa


revision = 'f6b8d0c2e4a7'
down_revision = 'e5a7c9b1d3f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('school_config', sa.Column('short_break_start', sa.String(length=10),
                                             nullable=True, server_default='10:30'))
    op.add_column('school_config', sa.Column('short_break_end', sa.String(length=10),
                                             nullable=True, server_default='10:45'))
    # Drop the earlier placeholder columns now that the break is time-based.
    for col in ('short_break_after_period', 'short_break_duration'):
        try:
            op.drop_column('school_config', col)
        except Exception:
            pass
    op.add_column('timetable_slots', sa.Column('is_short_break', sa.Boolean(),
                                               nullable=True, server_default=sa.false()))


def downgrade():
    op.drop_column('timetable_slots', 'is_short_break')
    op.add_column('school_config', sa.Column('short_break_duration', sa.Integer(), server_default='10'))
    op.add_column('school_config', sa.Column('short_break_after_period', sa.Integer()))
    op.drop_column('school_config', 'short_break_end')
    op.drop_column('school_config', 'short_break_start')
