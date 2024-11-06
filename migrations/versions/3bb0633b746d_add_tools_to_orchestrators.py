"""Add tools to orchestrators

Revision ID: 3bb0633b746d
Revises: 22b22e75b323
Create Date: 2024-10-21 10:40:29.221709

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3bb0633b746d"
down_revision: Union[str, None] = "22b22e75b323"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usertoollink",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tool_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tool_id"], ["tool.id"], ondelete="CASCADE", name="fk_usertoollink_tool_id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            ondelete="CASCADE",
            name="fk_usertoollink_user_id",
        ),
        sa.PrimaryKeyConstraint("user_id", "tool_id"),
    )
    # Migrate data
    op.execute(
        """
        INSERT INTO usertoollink (user_id, tool_id)
        SELECT user_id, id FROM tool
    """
    )

    op.create_table(
        "orchestratortoollink",
        sa.Column("orchestrator_id", sa.Uuid(), nullable=False),
        sa.Column("tool_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["orchestrator_id"],
            ["orchestrator.id"],
            ondelete="CASCADE",
            name="fk_orchestratortoollink_orchestrator_id",
        ),
        sa.ForeignKeyConstraint(
            ["tool_id"],
            ["tool.id"],
            ondelete="CASCADE",
            name="fk_orchestratortoollink_tool_id",
        ),
        sa.PrimaryKeyConstraint("orchestrator_id", "tool_id"),
    )
    # No data to migrate

    op.create_index(op.f("ix_usertoollink_user_id"), "usertoollink", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_operatortoollink_operator_id"),
        "operatortoollink",
        ["operator_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orchestratortoollink_orchestrator_id"),
        "orchestratortoollink",
        ["orchestrator_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_operatortoollink_operator_id",
        "operatortoollink",
        "operator",
        ["operator_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("ix_user_toolname", "tool", type_="unique")
    op.drop_constraint("fk_tooluserid_userid", "tool", type_="foreignkey")
    op.drop_column("tool", "user_id")


def downgrade() -> None:
    op.add_column("tool", sa.Column("user_id", sa.UUID(), autoincrement=False, nullable=True))

    # Migrate data from 'usertoollink' back to 'tool'
    op.execute(
        """
        UPDATE tool
        SET user_id = (
            SELECT user_id
            FROM usertoollink
            WHERE usertoollink.tool_id = tool.id
        )
    """
    )
    op.alter_column("tool", "user_id", nullable=False)

    op.create_foreign_key("fk_tooluserid_userid", "tool", "user", ["user_id"], ["id"])
    op.create_unique_constraint("ix_user_toolname", "tool", ["user_id", "name"])

    op.drop_index(op.f("ix_operatortoollink_operator_id"), table_name="operatortoollink")
    op.drop_index(
        op.f("ix_orchestratortoollink_orchestrator_id"),
        table_name="orchestratortoollink",
    )
    op.drop_table("orchestratortoollink")
    op.drop_index(op.f("ix_usertoollink_user_id"), table_name="usertoollink")
    op.drop_table("usertoollink")
