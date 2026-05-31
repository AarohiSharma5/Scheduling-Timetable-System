"""teacher management: extended profile fields

Revision ID: b2d4f6a8c1e3
Revises: a1c2e3f4b5d6
Create Date: 2026-06-01

Adds to teachers:
  * gender
  * primary_subject / secondary_subject  - profile labels
  * experience_years
  * availability                          - Full-time/Part-time/Visiting/On Leave
  * status                                - active/inactive (default active)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2d4f6a8c1e3'
down_revision = 'a1c2e3f4b5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('teachers', sa.Column('gender', sa.String(length=20), nullable=True))
    op.add_column('teachers', sa.Column('primary_subject', sa.String(length=120), nullable=True))
    op.add_column('teachers', sa.Column('secondary_subject', sa.String(length=120), nullable=True))
    op.add_column('teachers', sa.Column('experience_years', sa.Integer(), nullable=True))
    op.add_column('teachers', sa.Column('availability', sa.String(length=40), nullable=True))
    op.add_column('teachers', sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))


def downgrade():
    op.drop_column('teachers', 'status')
    op.drop_column('teachers', 'availability')
    op.drop_column('teachers', 'experience_years')
    op.drop_column('teachers', 'secondary_subject')
    op.drop_column('teachers', 'primary_subject')
    op.drop_column('teachers', 'gender')
