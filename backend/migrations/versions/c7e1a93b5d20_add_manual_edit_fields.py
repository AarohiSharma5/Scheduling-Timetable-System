"""manual timetable editing: slot room/pin + timetable edit provenance

Revision ID: c7e1a93b5d20
Revises: b5c9f1a7d342
Create Date: 2026-05-31

Adds:
  * timetable_slots.room        - optional free-text room/lab (room conflict checks)
  * timetable_slots.is_pinned   - period manually locked, preserved on regeneration
  * timetables.edited_by        - user who last manually edited / created the version
  * timetables.edited_at        - when the manual edit happened
  * timetables.change_log       - append-only audit trail of manual changes (JSON)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7e1a93b5d20'
down_revision = 'b5c9f1a7d342'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('timetable_slots', sa.Column('room', sa.String(length=120), nullable=True))
    op.add_column('timetable_slots', sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('timetables', sa.Column('edited_by', sa.Integer(), nullable=True))
    op.add_column('timetables', sa.Column('edited_at', sa.DateTime(), nullable=True))
    op.add_column('timetables', sa.Column('change_log', sa.JSON(), nullable=True))

    with op.batch_alter_table('timetable_slots', schema=None) as batch_op:
        batch_op.alter_column('is_pinned', server_default=None)


def downgrade():
    op.drop_column('timetables', 'change_log')
    op.drop_column('timetables', 'edited_at')
    op.drop_column('timetables', 'edited_by')
    op.drop_column('timetable_slots', 'is_pinned')
    op.drop_column('timetable_slots', 'room')
