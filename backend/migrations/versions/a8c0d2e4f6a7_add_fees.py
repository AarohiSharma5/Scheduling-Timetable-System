"""add fee_structures + fee_invoices + fee_payments

Revision ID: a8c0d2e4f6a7
Revises: f7a9b1c3d5e6
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'a8c0d2e4f6a7'
down_revision = 'f7a9b1c3d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'fee_structures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('grade', sa.String(length=20), nullable=True),
        sa.Column('term', sa.String(length=50), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('fee_structures', schema=None) as b:
        b.create_index('ix_fee_structures_organization_id', ['organization_id'], unique=False)

    op.create_table(
        'fee_invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('fee_structure_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['fee_structure_id'], ['fee_structures.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'student_id', 'fee_structure_id',
                            name='uq_invoice_student_structure'),
    )
    with op.batch_alter_table('fee_invoices', schema=None) as b:
        b.create_index('ix_fee_invoices_organization_id', ['organization_id'], unique=False)
        b.create_index('ix_fee_invoices_student_id', ['student_id'], unique=False)

    op.create_table(
        'fee_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('method', sa.String(length=20), nullable=True),
        sa.Column('reference', sa.String(length=100), nullable=True),
        sa.Column('paid_on', sa.Date(), nullable=True),
        sa.Column('recorded_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['invoice_id'], ['fee_invoices.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('fee_payments', schema=None) as b:
        b.create_index('ix_fee_payments_organization_id', ['organization_id'], unique=False)
        b.create_index('ix_fee_payments_invoice_id', ['invoice_id'], unique=False)
        b.create_index('ix_fee_payments_student_id', ['student_id'], unique=False)


def downgrade():
    with op.batch_alter_table('fee_payments', schema=None) as b:
        b.drop_index('ix_fee_payments_student_id')
        b.drop_index('ix_fee_payments_invoice_id')
        b.drop_index('ix_fee_payments_organization_id')
    op.drop_table('fee_payments')
    with op.batch_alter_table('fee_invoices', schema=None) as b:
        b.drop_index('ix_fee_invoices_student_id')
        b.drop_index('ix_fee_invoices_organization_id')
    op.drop_table('fee_invoices')
    with op.batch_alter_table('fee_structures', schema=None) as b:
        b.drop_index('ix_fee_structures_organization_id')
    op.drop_table('fee_structures')
