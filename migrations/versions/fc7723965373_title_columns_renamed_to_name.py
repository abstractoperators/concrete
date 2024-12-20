"""title columns renamed to name

Revision ID: fc7723965373
Revises: cb991c369855
Create Date: 2024-10-15 14:12:08.625662

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fc7723965373"
down_revision: Union[str, None] = "cb991c369855"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("message", "type_name", new_column_name="type")

    op.add_column(
        "operator",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    )

    # Add unique names to existing operators
    old_operators = sa.Table(
        "operator",
        sa.MetaData(),
        sa.Column("id", sa.Uuid()),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=64)),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=32)),
    )
    # Use Alchemy's connection and transaction to noodle over the data.
    connection = op.get_bind()
    # Select all existing names that need migrating.
    results = connection.execute(
        sa.select(
            old_operators.c.id,
            old_operators.c.title,
        )
    ).fetchall()
    # Iterate over all selected data tuples.
    for i, (id, title) in enumerate(results):
        # Split the existing name into first and last.
        new_name = f"{title}{i}"
        # Update the new columns.
        connection.execute(old_operators.update().where(old_operators.c.id == id).values(name=new_name))
    # Alter column to be not nullable
    op.alter_column("operator", "name", nullable=False)

    op.create_unique_constraint(
        "no_duplicate_operators_per_orchestrator",
        "operator",
        ["name", "orchestrator_id"],
    )
    op.alter_column("orchestrator", "type_name", new_column_name="type")
    op.alter_column("orchestrator", "title", new_column_name="name")
    op.create_unique_constraint("no_duplicate_names_per_user", "orchestrator", ["name", "user_id"])

    op.alter_column("project", "title", new_column_name="name")
    op.create_unique_constraint("no_duplicate_projects_per_orchestrator", "project", ["name", "orchestrator_id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("no_duplicate_projects_per_orchestrator", "project", type_="unique")
    op.alter_column("project", "name", new_column_name="title")

    op.drop_constraint("no_duplicate_names_per_user", "orchestrator", type_="unique")
    op.alter_column("orchestrator", "name", new_column_name="title")
    op.alter_column("orchestrator", "type", new_column_name="type_name")

    op.drop_constraint("no_duplicate_operators_per_orchestrator", "operator", type_="unique")
    op.drop_column("operator", "name")

    op.alter_column("message", "type", new_column_name="type_name")
    # ### end Alembic commands ###
