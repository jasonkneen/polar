"""Add unique constraint on ExternalEvent source+external_id

Revision ID: 0db0550375a5
Revises: 358d9fbe3de4
Create Date: 2025-03-17 15:03:50.457123

"""

import sqlalchemy as sa
from alembic import op

# Polar Custom Imports

# revision identifiers, used by Alembic.
revision = "0db0550375a5"
down_revision = "358d9fbe3de4"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(
        op.f("external_events_source_external_id_key"),
        "external_events",
        ["source", "external_id"],
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("external_events_source_external_id_key"),
        "external_events",
        type_="unique",
    )
    # ### end Alembic commands ###
