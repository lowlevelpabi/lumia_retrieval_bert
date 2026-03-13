"""add_imrad_summary_columns

Revision ID: c9c9cd53d226
Revises: 
Create Date: 2026-03-13 17:49:44.018992

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9c9cd53d226'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('papers', sa.Column('introduction_summary', sa.Text(), nullable=True))
    op.add_column('papers', sa.Column('methods_summary', sa.Text(), nullable=True))
    op.add_column('papers', sa.Column('results_summary', sa.Text(), nullable=True))
    op.add_column('papers', sa.Column('discussion_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('papers', 'discussion_summary')
    op.drop_column('papers', 'results_summary')
    op.drop_column('papers', 'methods_summary')
    op.drop_column('papers', 'introduction_summary')