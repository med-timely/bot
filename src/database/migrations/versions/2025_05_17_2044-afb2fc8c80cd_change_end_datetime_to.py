"""Change end_datetime to be non-computed

Revision ID: afb2fc8c80cd
Revises: 35b67a0ec1f3
Create Date: 2025-05-17 20:44:21.362646

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "afb2fc8c80cd"
down_revision: Union[str, None] = "35b67a0ec1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop computed end_datetime column
    op.drop_column("schedules", "end_datetime")

    # Add new end_datetime column
    op.add_column(
        "schedules",
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=True),
    )

    # Populate existing rows
    op.execute(
        """
        UPDATE `schedules`
        SET `end_datetime` = `start_datetime` + INTERVAL `duration` DAY
        WHERE `duration` IS NOT NULL
    """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new columns
    op.drop_column("schedules", "end_datetime")

    # Restore original computed end_datetime
    op.add_column(
        "schedules",
        sa.Column(
            "end_datetime",
            sa.DateTime(timezone=True),
            sa.Computed("start_datetime + INTERVAL duration DAY"),
            nullable=True,
        ),
    )
