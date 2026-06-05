"""add guardians + announcements tables

Revision ID: f7a9b1c3d5e6
Revises: e6f8a0b2c4d5
Create Date: 2026-06-05

Parent/guardian login linkage (guardians) and staff broadcasts
(announcements), both scoped per organization.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7a9b1c3d5e6'
down_revision = 'e6f8a0b2c4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'guardians',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('relation', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'student_id', name='uq_guardian_user_student'),
    )
    with op.batch_alter_table('guardians', schema=None) as batch_op:
        batch_op.create_index('ix_guardians_organization_id', ['organization_id'], unique=False)
        batch_op.create_index('ix_guardians_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_guardians_student_id', ['student_id'], unique=False)

    op.create_table(
        'announcements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('audience', sa.String(length=20), nullable=False, server_default='all'),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.create_index('ix_announcements_organization_id', ['organization_id'], unique=False)


def downgrade():
    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.drop_index('ix_announcements_organization_id')
    op.drop_table('announcements')
    with op.batch_alter_table('guardians', schema=None) as batch_op:
        batch_op.drop_index('ix_guardians_student_id')
        batch_op.drop_index('ix_guardians_user_id')
        batch_op.drop_index('ix_guardians_organization_id')
    op.drop_table('guardians')
