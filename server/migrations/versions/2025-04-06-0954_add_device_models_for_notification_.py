"""add device models for notification recipients

Revision ID: 315e7ca08fee
Revises: 301eb03ce91c
Create Date: 2025-04-06 09:54:45.566699

"""

import sqlalchemy as sa
from alembic import op

# Polar Custom Imports

# revision identifiers, used by Alembic.
revision = "315e7ca08fee"
down_revision = "301eb03ce91c"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "devices",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("expo_push_token", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("devices_user_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("devices_pkey")),
    )
    op.create_index(
        op.f("ix_devices_created_at"), "devices", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_devices_deleted_at"), "devices", ["deleted_at"], unique=False
    )
    op.create_index(
        op.f("ix_devices_modified_at"), "devices", ["modified_at"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_devices_modified_at"), table_name="devices")
    op.drop_index(op.f("ix_devices_deleted_at"), table_name="devices")
    op.drop_index(op.f("ix_devices_created_at"), table_name="devices")
    op.drop_table("devices")
    # ### end Alembic commands ###
