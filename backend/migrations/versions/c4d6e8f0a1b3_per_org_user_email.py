"""make user email unique per organization instead of globally

Revision ID: c4d6e8f0a1b3
Revises: b3c5d7e9f1a2
Create Date: 2026-06-04

Drops the global UNIQUE(email) on users and replaces it with a composite
UNIQUE(organization_id, email). This lets two different schools (tenants) each
have a user with the same email address, while still preventing duplicates
within a single organization.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c4d6e8f0a1b3'
down_revision = 'b3c5d7e9f1a2'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('users_email_key', 'users', type_='unique')
    op.create_unique_constraint(
        'uq_users_org_email', 'users', ['organization_id', 'email']
    )


def downgrade():
    op.drop_constraint('uq_users_org_email', 'users', type_='unique')
    op.create_unique_constraint('users_email_key', 'users', ['email'])
