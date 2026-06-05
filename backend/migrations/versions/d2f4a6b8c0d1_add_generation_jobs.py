"""add generation_jobs

Revision ID: d2f4a6b8c0d1
Revises: c1e2f3a4b5c6
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'd2f4a6b8c0d1'
down_revision = 'c1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'generation_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('timetable_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='queued'),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['timetable_id'], ['timetables.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('generation_jobs', schema=None) as b:
        b.create_index('ix_generation_jobs_organization_id', ['organization_id'], unique=False)
        b.create_index('ix_generation_jobs_status', ['status'], unique=False)


def downgrade():
    with op.batch_alter_table('generation_jobs', schema=None) as b:
        b.drop_index('ix_generation_jobs_status')
        b.drop_index('ix_generation_jobs_organization_id')
    op.drop_table('generation_jobs')
