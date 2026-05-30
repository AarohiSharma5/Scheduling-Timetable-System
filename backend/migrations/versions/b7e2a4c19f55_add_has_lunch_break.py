"""add has_lunch_break to school_config

Revision ID: b7e2a4c19f55
Revises: f3a9c1d24b80
Create Date: 2026-05-30

Lets an admin choose between a timetable with an explicit lunch break and a
compact, back-to-back schedule. Existing rows default to having a lunch break.

NOTE: This file was restored after being accidentally removed; the column may
already exist on databases that applied the original. The body is written to be
the source of truth for fresh builds.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e2a4c19f55'
down_revision = 'f3a9c1d24b80'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('school_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'has_lunch_break', sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table('school_config', schema=None) as batch_op:
        batch_op.alter_column('has_lunch_break', server_default=None)


def downgrade():
    with op.batch_alter_table('school_config', schema=None) as batch_op:
        batch_op.drop_column('has_lunch_break')
