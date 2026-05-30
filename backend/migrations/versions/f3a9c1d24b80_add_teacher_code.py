"""add teacher_code to teachers

Revision ID: f3a9c1d24b80
Revises: e7481122c712
Create Date: 2026-05-30

Adds a human-readable employee id (e.g. "TCHR0001") to teachers so they can be
identified on exports and dashboards without exposing the internal DB id.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a9c1d24b80'
down_revision = 'e7481122c712'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('teachers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('teacher_code', sa.String(length=50), nullable=True))
        batch_op.create_index('ix_teachers_teacher_code', ['teacher_code'], unique=False)


def downgrade():
    with op.batch_alter_table('teachers', schema=None) as batch_op:
        batch_op.drop_index('ix_teachers_teacher_code')
        batch_op.drop_column('teacher_code')
