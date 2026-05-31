"""charges catalog, structured teaching assignments, dynamic contact hours

Revision ID: f3a1d2b6c890
Revises: e2c7a9114f08
Create Date: 2026-05-31

Adds:
  * charges            - admin-defined catalog of non-teaching duties
  * teachers.teaching_assignments (JSON) - per-subject batch lists
  * teachers.charges              (JSON) - assigned duties + weekly hours
  * school_config.target_contact_periods_per_week - common weekly load target
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a1d2b6c890'
down_revision = 'e2c7a9114f08'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'charges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('default_hours_per_week', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_charges_organization_id', 'charges', ['organization_id'], unique=False)

    op.add_column('teachers', sa.Column('teaching_assignments', sa.JSON(), nullable=True))
    op.add_column('teachers', sa.Column('charges', sa.JSON(), nullable=True))

    op.add_column(
        'school_config',
        sa.Column('target_contact_periods_per_week', sa.Integer(), nullable=False, server_default='40'),
    )
    with op.batch_alter_table('school_config', schema=None) as batch_op:
        batch_op.alter_column('target_contact_periods_per_week', server_default=None)
    with op.batch_alter_table('charges', schema=None) as batch_op:
        batch_op.alter_column('default_hours_per_week', server_default=None)


def downgrade():
    op.drop_column('school_config', 'target_contact_periods_per_week')
    op.drop_column('teachers', 'charges')
    op.drop_column('teachers', 'teaching_assignments')
    op.drop_index('ix_charges_organization_id', table_name='charges')
    op.drop_table('charges')
