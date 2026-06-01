"""rooms / facilities + classroom capacity-driven distribution

Revision ID: c3e5a7b9d1f2
Revises: b2d4f6a8c1e3
Create Date: 2026-06-01

Adds:
  * school_config.default_room_capacity          (default 50)
  * school_config.ground_max_concurrent_batches  (default 4)
  * classrooms.organization_id                   (org-scoped rooms)
  * classrooms unique (organization_id, room_id) replacing global room_id unique
  * batches.room_id   - fixed home classroom
  * batches.capacity  - effective section capacity

Legacy (non-org-scoped) classroom rows are cleared; rooms are re-seeded per org.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3e5a7b9d1f2'
down_revision = 'b2d4f6a8c1e3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('school_config', sa.Column(
        'default_room_capacity', sa.Integer(), nullable=False, server_default='50'))
    op.add_column('school_config', sa.Column(
        'ground_max_concurrent_batches', sa.Integer(), nullable=False, server_default='4'))

    # Legacy classrooms were global (no organization); drop them so we can make
    # the table multi-tenant cleanly, then re-seed per organization.
    op.execute("DELETE FROM classrooms")
    op.add_column('classrooms', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_classrooms_org', 'classrooms', 'organizations',
        ['organization_id'], ['id'])
    op.create_index('ix_classrooms_organization_id', 'classrooms', ['organization_id'])
    # Replace the global unique(room_id) with a per-org composite unique.
    op.drop_constraint('classrooms_room_id_key', 'classrooms', type_='unique')
    op.create_unique_constraint(
        'uq_classroom_org_code', 'classrooms', ['organization_id', 'room_id'])
    # room_type now has an app-level default of "regular".
    op.alter_column('classrooms', 'room_type',
                    existing_type=sa.String(length=100),
                    server_default='regular')

    op.add_column('batches', sa.Column('room_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_batches_room', 'batches', 'classrooms', ['room_id'], ['id'])
    op.add_column('batches', sa.Column('capacity', sa.Integer(), nullable=True))


def downgrade():
    op.drop_constraint('fk_batches_room', 'batches', type_='foreignkey')
    op.drop_column('batches', 'capacity')
    op.drop_column('batches', 'room_id')

    op.drop_constraint('uq_classroom_org_code', 'classrooms', type_='unique')
    op.drop_index('ix_classrooms_organization_id', table_name='classrooms')
    op.drop_constraint('fk_classrooms_org', 'classrooms', type_='foreignkey')
    op.drop_column('classrooms', 'organization_id')
    op.create_unique_constraint('classrooms_room_id_key', 'classrooms', ['room_id'])

    op.drop_column('school_config', 'ground_max_concurrent_batches')
    op.drop_column('school_config', 'default_room_capacity')
