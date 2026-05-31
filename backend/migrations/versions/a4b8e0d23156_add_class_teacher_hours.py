"""add coordinator-entered class teacher hours

Revision ID: a4b8e0d23156
Revises: f3a1d2b6c890
Create Date: 2026-05-31

Adds school_config.class_teacher_hours_per_week — extra weekly contact hours
reserved for class teachers. Defaults to 0 (the system never assumes a value;
the coordinator specifies it).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4b8e0d23156'
down_revision = 'f3a1d2b6c890'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'school_config',
        sa.Column('class_teacher_hours_per_week', sa.Integer(), nullable=False, server_default='0'),
    )
    with op.batch_alter_table('school_config', schema=None) as batch_op:
        batch_op.alter_column('class_teacher_hours_per_week', server_default=None)


def downgrade():
    op.drop_column('school_config', 'class_teacher_hours_per_week')
