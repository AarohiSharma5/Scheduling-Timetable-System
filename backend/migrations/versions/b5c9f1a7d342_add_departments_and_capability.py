"""departments (member counts + takes_classes) and grade-level teacher capability

Revision ID: b5c9f1a7d342
Revises: a4b8e0d23156
Create Date: 2026-05-31

Adds:
  * charges.members_required  - how many teachers staff a department
  * charges.takes_classes     - False => substitute-only pool (Library/Fees)
  * teachers.subject_grades   - capability by subject + grades (JSON)
  * teachers.takes_classes    - denormalized: member of a non-teaching dept?
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5c9f1a7d342'
down_revision = 'a4b8e0d23156'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('charges', sa.Column('members_required', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('charges', sa.Column('takes_classes', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('teachers', sa.Column('subject_grades', sa.JSON(), nullable=True))
    op.add_column('teachers', sa.Column('takes_classes', sa.Boolean(), nullable=False, server_default=sa.true()))

    for table, col in [('charges', 'members_required'), ('charges', 'takes_classes'),
                       ('teachers', 'takes_classes')]:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(col, server_default=None)


def downgrade():
    op.drop_column('teachers', 'takes_classes')
    op.drop_column('teachers', 'subject_grades')
    op.drop_column('charges', 'takes_classes')
    op.drop_column('charges', 'members_required')
