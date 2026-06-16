"""add org_id indexes and fks

Revision ID: e7481122c712
Revises: 19d5f65d197c
Create Date: 2026-05-30 07:57:54.595324

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'e7481122c712'
down_revision = '19d5f65d197c'
branch_labels = None
depends_on = None


# Tables that get an index + FK on organization_id. On databases created from
# the current baseline these already exist (the baseline absorbed them), so this
# migration must be idempotent: create each only when missing. That keeps it
# safe on both fresh DBs and older ones that predate the baseline change.
_TABLES = [
    'batches', 'leave_requests', 'school_config', 'students',
    'subjects', 'teachers', 'timetable_slots', 'timetables',
]


def _index_names(insp, table):
    return {ix['name'] for ix in insp.get_indexes(table)}


def _has_org_fk(insp, table):
    for fk in insp.get_foreign_keys(table):
        if (fk.get('referred_table') == 'organizations'
                and 'organization_id' in (fk.get('constrained_columns') or [])):
            return True
    return False


def upgrade():
    insp = inspect(op.get_bind())
    for table in _TABLES:
        idx_name = f'ix_{table}_organization_id'
        existing = _index_names(insp, table)
        has_fk = _has_org_fk(insp, table)
        with op.batch_alter_table(table, schema=None) as batch_op:
            if idx_name not in existing:
                batch_op.create_index(batch_op.f(idx_name), ['organization_id'], unique=False)
            if not has_fk:
                batch_op.create_foreign_key(None, 'organizations', ['organization_id'], ['id'])


def downgrade():
    insp = inspect(op.get_bind())
    for table in reversed(_TABLES):
        idx_name = f'ix_{table}_organization_id'
        if idx_name in _index_names(insp, table):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_index(batch_op.f(idx_name))
