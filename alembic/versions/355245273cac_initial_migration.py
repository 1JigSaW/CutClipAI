"""Initial migration

Revision ID: 355245273cac
Revises: 
Create Date: 2025-11-26 00:45:14.409505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '355245273cac'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('balance', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_users_id',
        'users',
        ['id'],
        unique=False,
    )
    op.create_index(
        'ix_users_telegram_id',
        'users',
        ['telegram_id'],
        unique=True,
    )

    op.create_table(
        'transactions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.Enum('PURCHASE', 'CHARGE', 'REFUND', name='transactiontype'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_transactions_id',
        'transactions',
        ['id'],
        unique=False,
    )
    op.create_index(
        'ix_transactions_user_id',
        'transactions',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        'ix_transactions_created_at',
        'transactions',
        ['created_at'],
        unique=False,
    )

    op.create_table(
        'video_tasks',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='taskstatus'), nullable=False, server_default='PENDING'),
        sa.Column('input_file_path', sa.String(), nullable=True),
        sa.Column('output_file_path', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_video_tasks_id',
        'video_tasks',
        ['id'],
        unique=False,
    )
    op.create_index(
        'ix_video_tasks_task_id',
        'video_tasks',
        ['task_id'],
        unique=True,
    )
    op.create_index(
        'ix_video_tasks_user_id',
        'video_tasks',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        'ix_video_tasks_status',
        'video_tasks',
        ['status'],
        unique=False,
    )
    op.create_index(
        'ix_video_tasks_created_at',
        'video_tasks',
        ['created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_video_tasks_created_at', table_name='video_tasks')
    op.drop_index('ix_video_tasks_status', table_name='video_tasks')
    op.drop_index('ix_video_tasks_user_id', table_name='video_tasks')
    op.drop_index('ix_video_tasks_task_id', table_name='video_tasks')
    op.drop_index('ix_video_tasks_id', table_name='video_tasks')
    op.drop_table('video_tasks')

    op.drop_index('ix_transactions_created_at', table_name='transactions')
    op.drop_index('ix_transactions_user_id', table_name='transactions')
    op.drop_index('ix_transactions_id', table_name='transactions')
    op.drop_table('transactions')

    op.drop_index('ix_users_telegram_id', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')

    sa.Enum(name='taskstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='transactiontype').drop(op.get_bind(), checkfirst=True)
