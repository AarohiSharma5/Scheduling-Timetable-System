"""add attendance_records table

Revision ID: d5e7f9a1b3c4
Revises: c4d6e8f0a1b3
Create Date: 2026-06-04

Daily + period-wise student attendance, scoped per organization. A composite
unique (organization_id, student_id, date, period_number) makes re-marking
idempotent (period 0 == whole-day mark).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e7f9a1b3c4'
down_revision = 'c4d6e8f0a1b3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'attendance_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('period_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('subject_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='present'),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('marked_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.ForeignKeyConstraint(['marked_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'student_id', 'date', 'period_number',
                            name='uq_attendance_student_date_period'),
    )
    with op.batch_alter_table('attendance_records', schema=None) as batch_op:
        batch_op.create_index('ix_attendance_records_organization_id', ['organization_id'], unique=False)
        batch_op.create_index('ix_attendance_records_student_id', ['student_id'], unique=False)
        batch_op.create_index('ix_attendance_records_batch_id', ['batch_id'], unique=False)
        batch_op.create_index('ix_attendance_records_date', ['date'], unique=False)


def downgrade():
    with op.batch_alter_table('attendance_records', schema=None) as batch_op:
        batch_op.drop_index('ix_attendance_records_date')
        batch_op.drop_index('ix_attendance_records_batch_id')
        batch_op.drop_index('ix_attendance_records_student_id')
        batch_op.drop_index('ix_attendance_records_organization_id')
    op.drop_table('attendance_records')
