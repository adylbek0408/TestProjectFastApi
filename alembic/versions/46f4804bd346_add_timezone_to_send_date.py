"""Add timezone to send_date

Revision ID: 46f4804bd346
Revises: 2bf3ee2d5bc5
Create Date: 2024-09-30 19:31:04.566917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '46f4804bd346'
down_revision: Union[str, None] = '2bf3ee2d5bc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Приводим столбец send_date к типу TIMESTAMP WITH TIME ZONE
    op.alter_column('notifications', 'send_date',
                    existing_type=sa.TIMESTAMP(),
                    type_=sa.TIMESTAMP(timezone=True),
                    existing_nullable=False)


def downgrade():
    # Возвращаем столбец send_date к типу TIMESTAMP без временной зоны
    op.alter_column('notifications', 'send_date',
                    existing_type=sa.TIMESTAMP(timezone=True),
                    type_=sa.TIMESTAMP(),
                    existing_nullable=False)

