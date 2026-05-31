"""student & teacher management: profile fields

Revision ID: f0a1b2c3d4e5
Revises: c7e1a93b5d20
Create Date: 2026-05-31

Adds:
  * students.email                - optional student/parent contact email
  * students.gender / dob          - relaxed to NULLable (new lightweight form)
  * teachers.phone                 - contact number
  * teachers.qualification         - e.g. "M.Sc, B.Ed"
  * teachers.designation           - e.g. "Coordinator", "PGT"
  * teachers.joining_date          - date the teacher joined
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0a1b2c3d4e5'
down_revision = 'c7e1a93b5d20'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('students', sa.Column('email', sa.String(length=120), nullable=True))
    op.add_column('teachers', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('teachers', sa.Column('qualification', sa.String(length=200), nullable=True))
    op.add_column('teachers', sa.Column('designation', sa.String(length=120), nullable=True))
    op.add_column('teachers', sa.Column('joining_date', sa.Date(), nullable=True))

    # New lightweight student-entry form doesn't collect gender/DOB, so relax the
    # NOT NULL constraints that the original demographic-heavy schema had.
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.alter_column('gender', existing_type=sa.String(length=20), nullable=True)
        batch_op.alter_column('date_of_birth', existing_type=sa.Date(), nullable=True)


def downgrade():
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.alter_column('date_of_birth', existing_type=sa.Date(), nullable=False)
        batch_op.alter_column('gender', existing_type=sa.String(length=20), nullable=False)

    op.drop_column('teachers', 'joining_date')
    op.drop_column('teachers', 'designation')
    op.drop_column('teachers', 'qualification')
    op.drop_column('teachers', 'phone')
    op.drop_column('students', 'email')
