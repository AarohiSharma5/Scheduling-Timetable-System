"""add assignments + assignment_submissions

Revision ID: b9d1e3f5a7b8
Revises: a8c0d2e4f6a7
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'b9d1e3f5a7b8'
down_revision = 'a8c0d2e4f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('assignments', schema=None) as b:
        b.create_index('ix_assignments_organization_id', ['organization_id'], unique=False)
        b.create_index('ix_assignments_batch_id', ['batch_id'], unique=False)

    op.create_table(
        'assignment_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='submitted'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('grade', sa.String(length=20), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['assignment_id'], ['assignments.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assignment_id', 'student_id', name='uq_submission_assignment_student'),
    )
    with op.batch_alter_table('assignment_submissions', schema=None) as b:
        b.create_index('ix_assignment_submissions_organization_id', ['organization_id'], unique=False)
        b.create_index('ix_assignment_submissions_assignment_id', ['assignment_id'], unique=False)
        b.create_index('ix_assignment_submissions_student_id', ['student_id'], unique=False)


def downgrade():
    with op.batch_alter_table('assignment_submissions', schema=None) as b:
        b.drop_index('ix_assignment_submissions_student_id')
        b.drop_index('ix_assignment_submissions_assignment_id')
        b.drop_index('ix_assignment_submissions_organization_id')
    op.drop_table('assignment_submissions')
    with op.batch_alter_table('assignments', schema=None) as b:
        b.drop_index('ix_assignments_batch_id')
        b.drop_index('ix_assignments_organization_id')
    op.drop_table('assignments')
