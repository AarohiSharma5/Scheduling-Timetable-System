"""add school-assigned login_id to users (login by ID or email)

Revision ID: f4b6c8d0e2a3
Revises: e3a5b7c9d1f2
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa


revision = 'f4b6c8d0e2a3'
down_revision = 'e3a5b7c9d1f2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as b:
        b.add_column(sa.Column('login_id', sa.String(length=40), nullable=True))
        b.create_index('ix_users_login_id', ['login_id'])

    # Backfill existing accounts with a deterministic, per-role login ID. The
    # numeric suffix is the (globally unique) user id, so values are unique.
    op.execute(
        """
        UPDATE users SET login_id = (
            CASE lower(role)
                WHEN 'owner' THEN 'ADM'
                WHEN 'admin' THEN 'ADM'
                WHEN 'principal' THEN 'PRN'
                WHEN 'coordinator' THEN 'CRD'
                WHEN 'teacher' THEN 'TCH'
                WHEN 'student' THEN 'STU'
                WHEN 'parent' THEN 'PAR'
                ELSE 'USR'
            END
        ) || lpad(id::text, 4, '0')
        WHERE login_id IS NULL
        """
    )

    op.create_unique_constraint(
        'uq_users_org_login_id', 'users', ['organization_id', 'login_id']
    )


def downgrade():
    with op.batch_alter_table('users', schema=None) as b:
        b.drop_constraint('uq_users_org_login_id', type_='unique')
        b.drop_index('ix_users_login_id')
        b.drop_column('login_id')
