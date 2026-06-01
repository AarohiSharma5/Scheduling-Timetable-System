"""streams, subject combinations, electives & teaching groups

Revision ID: d4f6b8a0c2e5
Revises: c3e5a7b9d1f2
Create Date: 2026-06-01

Adds the dynamic stream / elective / teaching-group layer:
  * subjects.subject_type
  * students.stream / subject_combination / elective_subjects
  * school_config group + stream settings
  * streams, subject_combinations, teaching_groups, group_memberships tables
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f6b8a0c2e5'
down_revision = 'c3e5a7b9d1f2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('subjects', sa.Column('subject_type', sa.String(length=20),
                  nullable=False, server_default='core'))

    op.add_column('students', sa.Column('stream', sa.String(length=40), nullable=True))
    op.add_column('students', sa.Column('subject_combination', sa.String(length=80), nullable=True))
    op.add_column('students', sa.Column('elective_subjects', sa.JSON(), nullable=True))

    op.add_column('school_config', sa.Column('available_streams', sa.JSON(), nullable=True))
    op.add_column('school_config', sa.Column('stream_max_strength', sa.JSON(), nullable=True))
    op.add_column('school_config', sa.Column('min_group_size', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('school_config', sa.Column('max_group_size', sa.Integer(), nullable=False, server_default='45'))
    op.add_column('school_config', sa.Column('elective_merge_threshold', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('school_config', sa.Column('language_start_grade', sa.String(length=20), nullable=True, server_default='6'))
    op.add_column('school_config', sa.Column('allow_group_override', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        'streams',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), index=True),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('grade', sa.String(length=20), nullable=False),
        sa.Column('academic_year', sa.String(length=20)),
        sa.Column('max_strength', sa.Integer()),
        sa.Column('separate_sections', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('organization_id', 'grade', 'name', 'academic_year',
                            name='uq_stream_org_grade_name_year'),
    )

    op.create_table(
        'subject_combinations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), index=True),
        sa.Column('stream_id', sa.Integer(), sa.ForeignKey('streams.id')),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('grade', sa.String(length=20)),
        sa.Column('subject_ids', sa.JSON()),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table(
        'teaching_groups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), index=True),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('grade', sa.String(length=20), nullable=False),
        sa.Column('stream', sa.String(length=40)),
        sa.Column('section', sa.String(length=10)),
        sa.Column('group_type', sa.String(length=20), nullable=False, server_default='elective'),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id')),
        sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('teachers.id')),
        sa.Column('room_id', sa.Integer(), sa.ForeignKey('classrooms.id')),
        sa.Column('periods_per_week', sa.Integer()),
        sa.Column('block_key', sa.String(length=80)),
        sa.Column('locked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('auto_generated', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table(
        'group_memberships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), index=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('teaching_groups.id'), nullable=False, index=True),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('group_id', 'student_id', name='uq_group_membership'),
    )


def downgrade():
    op.drop_table('group_memberships')
    op.drop_table('teaching_groups')
    op.drop_table('subject_combinations')
    op.drop_table('streams')

    for col in ('allow_group_override', 'language_start_grade', 'elective_merge_threshold',
                'max_group_size', 'min_group_size', 'stream_max_strength', 'available_streams'):
        op.drop_column('school_config', col)

    op.drop_column('students', 'elective_subjects')
    op.drop_column('students', 'subject_combination')
    op.drop_column('students', 'stream')
    op.drop_column('subjects', 'subject_type')
