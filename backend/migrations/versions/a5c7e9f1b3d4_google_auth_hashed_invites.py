"""Google sign-in fields, hashed invitation tokens, token versioning

Revision ID: a5c7e9f1b3d4
Revises: f4b6c8d0e2a3
Create Date: 2026-06-10
"""
import hashlib

from alembic import op
import sqlalchemy as sa


revision = 'a5c7e9f1b3d4'
down_revision = 'f4b6c8d0e2a3'
branch_labels = None
depends_on = None


def upgrade():
    # --- users: Google linkage + profile photo + JWT invalidation counter ---
    with op.batch_alter_table('users', schema=None) as b:
        b.add_column(sa.Column('google_id', sa.String(length=64), nullable=True))
        b.add_column(sa.Column('profile_photo', sa.String(length=500), nullable=True))
        b.add_column(sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))
        b.create_index('ix_users_google_id', ['google_id'])

    # --- invitations: replace the plaintext token with its SHA-256 hash ---
    op.add_column('invitations', sa.Column('token_hash', sa.String(length=64), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, token FROM invitations")).fetchall()
    for row_id, token in rows:
        digest = hashlib.sha256((token or f"missing-{row_id}").encode()).hexdigest()
        conn.execute(
            sa.text("UPDATE invitations SET token_hash = :h WHERE id = :i"),
            {"h": digest, "i": row_id},
        )

    with op.batch_alter_table('invitations', schema=None) as b:
        b.alter_column('token_hash', nullable=False)
        b.create_index('ix_invitations_token_hash', ['token_hash'], unique=True)
        b.drop_column('token')


def downgrade():
    # The plaintext token is unrecoverable; restore the column using the hash
    # as a placeholder so the schema (not the data) is reverted.
    op.add_column('invitations', sa.Column('token', sa.String(length=120), nullable=True))
    op.execute("UPDATE invitations SET token = token_hash")
    with op.batch_alter_table('invitations', schema=None) as b:
        b.alter_column('token', nullable=False)
        b.create_index('ix_invitations_token', ['token'], unique=True)
        b.drop_index('ix_invitations_token_hash')
        b.drop_column('token_hash')

    with op.batch_alter_table('users', schema=None) as b:
        b.drop_index('ix_users_google_id')
        b.drop_column('token_version')
        b.drop_column('profile_photo')
        b.drop_column('google_id')
