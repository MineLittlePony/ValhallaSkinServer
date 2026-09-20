"""Add indexes to speed up requests

Revision ID: f27ad68ae23c
Revises: 74921986a8df
Create Date: 2026-09-20 14:06:40.525545

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f27ad68ae23c"
down_revision = "74921986a8df"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f("ix_textures_user_id"), "textures", ["user_id"], unique=False)
    op.create_index(op.f("ix_users_name"), "users", ["name"], unique=False)
    op.create_index(op.f("ix_users_uuid"), "users", ["uuid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_uuid"), table_name="users")
    op.drop_index(op.f("ix_users_name"), table_name="users")
    op.drop_index(op.f("ix_textures_user_id"), table_name="textures")
