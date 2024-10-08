"""create user_auth objects

Revision ID: b95be09d8b45
Revises: ad1893077e4f
Create Date: 2024-10-07 16:11:33.840957

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b95be09d8b45'
down_revision: Union[str, None] = 'ad1893077e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'authstate',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('state', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('destination_url', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'user',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('first_name', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('last_name', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('profile_picture', sqlmodel.sql.sqltypes.AutoString(length=256), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'authtoken',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('refresh_token', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column(
        'client', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.add_column(
        'client', sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    op.add_column(
        'message', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.add_column(
        'message', sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    op.add_column(
        'node', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.add_column(
        'node', sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    op.add_column(
        'operator', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.add_column(
        'operator', sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    op.add_column(
        'orchestrator',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.add_column(
        'orchestrator',
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.add_column('orchestrator', sa.Column('user_id', sa.Uuid(), nullable=False))
    op.create_foreign_key(None, 'orchestrator', 'user', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_column('orchestrator', 'owner')
    op.drop_column('orchestrator', 'foo')
    op.add_column(
        'reponode', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.add_column(
        'reponode', sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    op.add_column(
        'tool', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.add_column(
        'tool', sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tool', 'modified_at')
    op.drop_column('tool', 'created_at')
    op.drop_column('reponode', 'modified_at')
    op.drop_column('reponode', 'created_at')
    op.add_column('orchestrator', sa.Column('foo', sa.VARCHAR(length=32), autoincrement=False, nullable=False))
    op.add_column('orchestrator', sa.Column('owner', sa.VARCHAR(length=32), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'orchestrator', type_='foreignkey')
    op.drop_column('orchestrator', 'user_id')
    op.drop_column('orchestrator', 'modified_at')
    op.drop_column('orchestrator', 'created_at')
    op.drop_column('operator', 'modified_at')
    op.drop_column('operator', 'created_at')
    op.drop_column('node', 'modified_at')
    op.drop_column('node', 'created_at')
    op.drop_column('message', 'modified_at')
    op.drop_column('message', 'created_at')
    op.drop_column('client', 'modified_at')
    op.drop_column('client', 'created_at')
    op.drop_table('authtoken')
    op.drop_table('user')
    op.drop_table('authstate')
    # ### end Alembic commands ###
