"""add exams + exam_marks tables

Revision ID: e6f8a0b2c4d5
Revises: d5e7f9a1b3c4
Create Date: 2026-06-04

Assessments (exams) and per-student/per-subject marks, scoped per organization.
A composite unique (organization_id, exam_id, student_id, subject_id) makes
mark entry idempotent (re-entry updates in place).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6f8a0b2c4d5'
down_revision = 'd5e7f9a1b3c4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'exams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('term', sa.String(length=50), nullable=True),
        sa.Column('exam_type', sa.String(length=40), nullable=True),
        sa.Column('max_marks', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('exams', schema=None) as batch_op:
        batch_op.create_index('ix_exams_organization_id', ['organization_id'], unique=False)

    op.create_table(
        'exam_marks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('max_marks', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('marks_obtained', sa.Float(), nullable=True),
        sa.Column('is_absent', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('grade', sa.String(length=5), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('entered_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id']),
        sa.ForeignKeyConstraint(['entered_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'exam_id', 'student_id', 'subject_id',
                            name='uq_mark_exam_student_subject'),
    )
    with op.batch_alter_table('exam_marks', schema=None) as batch_op:
        batch_op.create_index('ix_exam_marks_organization_id', ['organization_id'], unique=False)
        batch_op.create_index('ix_exam_marks_exam_id', ['exam_id'], unique=False)
        batch_op.create_index('ix_exam_marks_student_id', ['student_id'], unique=False)
        batch_op.create_index('ix_exam_marks_subject_id', ['subject_id'], unique=False)


def downgrade():
    with op.batch_alter_table('exam_marks', schema=None) as batch_op:
        batch_op.drop_index('ix_exam_marks_subject_id')
        batch_op.drop_index('ix_exam_marks_student_id')
        batch_op.drop_index('ix_exam_marks_exam_id')
        batch_op.drop_index('ix_exam_marks_organization_id')
    op.drop_table('exam_marks')
    with op.batch_alter_table('exams', schema=None) as batch_op:
        batch_op.drop_index('ix_exams_organization_id')
    op.drop_table('exams')
