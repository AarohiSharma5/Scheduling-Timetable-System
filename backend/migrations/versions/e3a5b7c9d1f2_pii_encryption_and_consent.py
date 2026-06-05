"""widen PII columns for encryption + add consent tracking

Revision ID: e3a5b7c9d1f2
Revises: d2f4a6b8c0d1
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'e3a5b7c9d1f2'
down_revision = 'd2f4a6b8c0d1'
branch_labels = None
depends_on = None


# Encrypted ciphertext is much longer than the source value, so these columns
# must become TEXT.
_WIDEN = [
    ('father_name', sa.String(length=120)),
    ('mother_name', sa.String(length=120)),
    ('contact_number', sa.String(length=20)),
    ('blood_group', sa.String(length=10)),
]


def upgrade():
    with op.batch_alter_table('students', schema=None) as b:
        for col, _old in _WIDEN:
            b.alter_column(col, type_=sa.Text(), existing_nullable=True)
        b.add_column(sa.Column('consent_given', sa.Boolean(), nullable=True, server_default=sa.false()))
        b.add_column(sa.Column('consent_at', sa.DateTime(), nullable=True))
        b.add_column(sa.Column('consent_by', sa.Integer(), nullable=True))
        b.create_foreign_key('fk_students_consent_by_users', 'users', ['consent_by'], ['id'])


def downgrade():
    with op.batch_alter_table('students', schema=None) as b:
        b.drop_constraint('fk_students_consent_by_users', type_='foreignkey')
        b.drop_column('consent_by')
        b.drop_column('consent_at')
        b.drop_column('consent_given')
        for col, old in _WIDEN:
            b.alter_column(col, type_=old, existing_nullable=True)
