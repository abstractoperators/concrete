"""init

Revision ID: ad1893077e4f
Revises: 
Create Date: 2024-10-04 10:58:17.584346

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ad1893077e4f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "node",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["node.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "orchestrator",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type_name", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("owner", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("foo", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reponode",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("repo", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("partition_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("summary", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("children_summaries", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("abs_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("branch", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["reponode.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_org_repo", "reponode", ["org", "repo"], unique=False)
    op.create_index(op.f("ix_reponode_branch"), "reponode", ["branch"], unique=False)
    op.create_index(op.f("ix_reponode_org"), "reponode", ["org"], unique=False)
    op.create_index(op.f("ix_reponode_repo"), "reponode", ["repo"], unique=False)
    op.create_table(
        "tool",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("prompt", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("INIT", "READY", "WORKING", "WAITING", "FINISHED", name="projectstatus"),
            nullable=False,
        ),
        sa.Column("orchestrator_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["orchestrator_id"], ["orchestrator.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "operator",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instructions", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("orchestrator_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["orchestrator_id"], ["orchestrator.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "client",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("orchestrator_id", sa.Uuid(), nullable=False),
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["operator.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["orchestrator_id"],
            ["orchestrator.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "operatortoollink",
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("tool_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["operator.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tool_id"],
            ["tool.id"],
        ),
        sa.PrimaryKeyConstraint("operator_id", "tool_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("operatortoollink")
    op.drop_table("client")
    op.drop_table("operator")
    op.drop_table("message")
    op.drop_table("tool")
    op.drop_index(op.f("ix_reponode_repo"), table_name="reponode")
    op.drop_index(op.f("ix_reponode_org"), table_name="reponode")
    op.drop_index(op.f("ix_reponode_branch"), table_name="reponode")
    op.drop_index("ix_org_repo", table_name="reponode")
    op.drop_table("reponode")
    op.drop_table("orchestrator")
    op.drop_table("node")
    # ### end Alembic commands ###
