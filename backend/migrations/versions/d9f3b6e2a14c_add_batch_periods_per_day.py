"""add per-class day length

Revision ID: d9f3b6e2a14c
Revises: c4d8e1f7a920
Create Date: 2026-05-31

Adds batches.periods_per_day so younger grades can finish earlier than seniors.
Nullable: existing classes keep using the school-wide period count.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9f3b6e2a14c'
down_revision = 'c4d8e1f7a920'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('periods_per_day', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.drop_column('periods_per_day')
