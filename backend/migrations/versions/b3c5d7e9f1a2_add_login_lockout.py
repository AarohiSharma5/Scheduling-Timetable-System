"""add brute-force lockout fields to users

Revision ID: b3c5d7e9f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-04

Adds failed_login_attempts + locked_until so repeated failed logins temporarily
lock an account, mitigating password brute-forcing.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c5d7e9f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'failed_login_attempts', sa.Integer(),
            nullable=False, server_default='0',
        ))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')
