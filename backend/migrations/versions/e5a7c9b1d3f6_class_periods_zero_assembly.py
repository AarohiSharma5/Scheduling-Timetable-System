"""class-wise period planning, zero period, assembly, generation mode

Revision ID: e5a7c9b1d3f6
Revises: d4f6b8a0c2e5
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5a7c9b1d3f6'
down_revision = 'd4f6b8a0c2e5'
branch_labels = None
depends_on = None


def upgrade():
    sc = [
        ('generation_mode', sa.String(length=20), 'global'),
        ('class_teacher_first_period', sa.Boolean(), sa.false()),
        ('zero_period_enabled', sa.Boolean(), sa.false()),
        ('zero_period_start', sa.String(length=10), '07:30'),
        ('zero_period_duration', sa.Integer(), '30'),
        ('zero_period_in_hours', sa.Boolean(), sa.false()),
        ('zero_period_in_workload', sa.Boolean(), sa.false()),
        ('assembly_mode', sa.String(length=20), 'disabled'),
        ('assembly_duration', sa.Integer(), '20'),
        ('assembly_period', sa.Integer(), '1'),
        ('has_short_break', sa.Boolean(), sa.false()),
        ('short_break_duration', sa.Integer(), '10'),
    ]
    for name, type_, default in sc:
        kw = {}
        if default is not None:
            kw['server_default'] = default if not isinstance(default, str) else sa.text(f"'{default}'")
        nullable = name in ('zero_period_start',)
        op.add_column('school_config', sa.Column(name, type_, nullable=False if not nullable else True, **kw))
    op.add_column('school_config', sa.Column('zero_period_grades', sa.JSON(), nullable=True))
    op.add_column('school_config', sa.Column('assembly_grades', sa.JSON(), nullable=True))
    op.add_column('school_config', sa.Column('assembly_schedule', sa.JSON(), nullable=True))
    op.add_column('school_config', sa.Column('short_break_after_period', sa.Integer(), nullable=True))

    op.create_table(
        'class_subject_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), index=True),
        sa.Column('grade', sa.String(length=20), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id'), nullable=False),
        sa.Column('periods_per_week', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('min_periods', sa.Integer()),
        sa.Column('max_periods', sa.Integer()),
        sa.Column('max_per_day', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('allow_consecutive', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('allow_daily', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('priority', sa.String(length=10), nullable=False, server_default='medium'),
        sa.Column('preferred_spread', sa.String(length=20), server_default='even'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.UniqueConstraint('organization_id', 'grade', 'subject_id', name='uq_class_subject_cfg'),
    )


def downgrade():
    op.drop_table('class_subject_configs')
    for name in ('short_break_after_period', 'assembly_schedule', 'assembly_grades', 'zero_period_grades',
                 'short_break_duration', 'has_short_break', 'assembly_period', 'assembly_duration',
                 'assembly_mode', 'zero_period_in_workload', 'zero_period_in_hours', 'zero_period_duration',
                 'zero_period_start', 'zero_period_enabled', 'class_teacher_first_period', 'generation_mode'):
        op.drop_column('school_config', name)
