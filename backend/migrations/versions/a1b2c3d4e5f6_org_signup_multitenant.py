"""Org self-signup, user lifecycle fields, invitations + audit logs

Revision ID: a1b2c3d4e5f6
Revises: f6b8d0c2e4a7
Create Date: 2026-06-02

Adds:
- organizations: school_code, board, address, city, state, country, postal_code,
  contact_number, official_email, website, academic_year, onboarding_step,
  onboarding_completed, is_active
- users: phone, designation, status, must_change_password, profile_completed,
  terms_accepted_at, created_by_id
- invitations table
- audit_logs table
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f6b8d0c2e4a7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("school_code", sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column("board", sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column("address", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("city", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("state", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("country", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("postal_code", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("contact_number", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("official_email", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("website", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("academic_year", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("onboarding_step", sa.Integer(), nullable=True, server_default="0"))
        batch_op.add_column(sa.Column("onboarding_completed", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.create_index("ix_organizations_school_code", ["school_code"], unique=True)
        batch_op.create_index("ix_organizations_official_email", ["official_email"], unique=False)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("phone", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("designation", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=True, server_default="active"))
        batch_op.add_column(sa.Column("must_change_password", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column("profile_completed", sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))

    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("invited_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_invitations_organization_id", "invitations", ["organization_id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])
    op.create_index("ix_invitations_token", "invitations", ["token"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("invitations")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("created_by_id")
        batch_op.drop_column("terms_accepted_at")
        batch_op.drop_column("profile_completed")
        batch_op.drop_column("must_change_password")
        batch_op.drop_column("status")
        batch_op.drop_column("designation")
        batch_op.drop_column("phone")

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_index("ix_organizations_official_email")
        batch_op.drop_index("ix_organizations_school_code")
        batch_op.drop_column("is_active")
        batch_op.drop_column("onboarding_completed")
        batch_op.drop_column("onboarding_step")
        batch_op.drop_column("academic_year")
        batch_op.drop_column("website")
        batch_op.drop_column("official_email")
        batch_op.drop_column("contact_number")
        batch_op.drop_column("postal_code")
        batch_op.drop_column("country")
        batch_op.drop_column("state")
        batch_op.drop_column("city")
        batch_op.drop_column("address")
        batch_op.drop_column("board")
        batch_op.drop_column("school_code")
