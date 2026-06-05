"""add calendar, library, transport, inventory, messaging tables

Revision ID: c1e2f3a4b5c6
Revises: b9d1e3f5a7b8
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'c1e2f3a4b5c6'
down_revision = 'b9d1e3f5a7b8'
branch_labels = None
depends_on = None


def upgrade():
    # --- calendar ---
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False, server_default='event'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('calendar_events', schema=None) as b:
        b.create_index('ix_calendar_events_organization_id', ['organization_id'], unique=False)

    # --- library ---
    op.create_table(
        'library_books',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=250), nullable=False),
        sa.Column('author', sa.String(length=150), nullable=True),
        sa.Column('isbn', sa.String(length=40), nullable=True),
        sa.Column('category', sa.String(length=80), nullable=True),
        sa.Column('total_copies', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('available_copies', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('library_books', schema=None) as b:
        b.create_index('ix_library_books_organization_id', ['organization_id'], unique=False)

    op.create_table(
        'library_loans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('issued_on', sa.Date(), nullable=True),
        sa.Column('due_on', sa.Date(), nullable=True),
        sa.Column('returned_on', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='issued'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['book_id'], ['library_books.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('library_loans', schema=None) as b:
        b.create_index('ix_library_loans_organization_id', ['organization_id'], unique=False)
        b.create_index('ix_library_loans_book_id', ['book_id'], unique=False)
        b.create_index('ix_library_loans_student_id', ['student_id'], unique=False)

    # --- transport ---
    op.create_table(
        'transport_routes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('driver_name', sa.String(length=120), nullable=True),
        sa.Column('driver_phone', sa.String(length=40), nullable=True),
        sa.Column('vehicle_no', sa.String(length=40), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('transport_routes', schema=None) as b:
        b.create_index('ix_transport_routes_organization_id', ['organization_id'], unique=False)

    op.create_table(
        'transport_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('stop_name', sa.String(length=150), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['route_id'], ['transport_routes.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('route_id', 'student_id', name='uq_transport_route_student'),
    )
    with op.batch_alter_table('transport_assignments', schema=None) as b:
        b.create_index('ix_transport_assignments_organization_id', ['organization_id'], unique=False)
        b.create_index('ix_transport_assignments_route_id', ['route_id'], unique=False)
        b.create_index('ix_transport_assignments_student_id', ['student_id'], unique=False)

    # --- inventory ---
    op.create_table(
        'inventory_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unit', sa.String(length=30), nullable=True),
        sa.Column('min_quantity', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=120), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('inventory_items', schema=None) as b:
        b.create_index('ix_inventory_items_organization_id', ['organization_id'], unique=False)

    # --- messaging ---
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('messages', schema=None) as b:
        b.create_index('ix_messages_organization_id', ['organization_id'], unique=False)
        b.create_index('ix_messages_sender_id', ['sender_id'], unique=False)
        b.create_index('ix_messages_recipient_id', ['recipient_id'], unique=False)
        b.create_index('ix_messages_created_at', ['created_at'], unique=False)


def downgrade():
    for tbl in ('messages', 'inventory_items', 'transport_assignments',
                'transport_routes', 'library_loans', 'library_books', 'calendar_events'):
        op.drop_table(tbl)
