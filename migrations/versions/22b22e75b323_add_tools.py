"""Add tools

Revision ID: 22b22e75b323
Revises: fc7723965373
Create Date: 2024-10-17 12:09:36.750912

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "22b22e75b323"
down_revision: Union[str, None] = "fc7723965373"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Update tool name for null names to be id
    op.add_column(
        "tool",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    )
    old_tools = sa.Table(
        "tool",
        sa.MetaData(),
        sa.Column("id", sa.Uuid()),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=64)),
    )
    connection = op.get_bind()
    results = connection.execute(
        sa.select(
            old_tools.c.id,
        )
    ).fetchall()
    for i, (id,) in enumerate(results):
        new_name = id
        connection.execute(old_tools.update().where(old_tools.c.id == id).values(name=new_name))
    op.alter_column("tool", "name", nullable=False)

    # Delete all tools that have no user
    op.add_column("tool", sa.Column("user_id", sa.Uuid(), nullable=True))
    old_tools = sa.Table(
        "tool",
        sa.MetaData(),
        sa.Column("id", sa.Uuid()),
        sa.Column("user_id", sa.Uuid()),
    )
    connection.execute(old_tools.delete().where(old_tools.c.user_id == None))
    op.alter_column("tool", "user_id", nullable=False)

    op.create_foreign_key("fk_tooluserid_userid", "tool", "user", ["user_id"], ["id"])
    op.create_unique_constraint("ix_user_toolname", "tool", ["user_id", "name"])


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("ix_user_toolname", "tool", type_="unique")
    op.drop_constraint("fk_tooluserid_userid", "tool", type_="foreignkey")
    op.drop_column("tool", "user_id")
    op.drop_column("tool", "name")
    # ### end Alembic commands ###
