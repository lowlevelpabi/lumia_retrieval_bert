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
    # Use inspector to check if columns already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('papers')]

    if 'introduction_summary' not in columns:
        op.add_column('papers', sa.Column('introduction_summary', sa.Text(), nullable=True))
    if 'methods_summary' not in columns:
        op.add_column('papers', sa.Column('methods_summary', sa.Text(), nullable=True))
    if 'results_summary' not in columns:
        op.add_column('papers', sa.Column('results_summary', sa.Text(), nullable=True))
    if 'discussion_summary' not in columns:
        op.add_column('papers', sa.Column('discussion_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    # Use inspector to check if columns exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('papers')]

    if 'discussion_summary' in columns:
        op.drop_column('papers', 'discussion_summary')
    if 'results_summary' in columns:
        op.drop_column('papers', 'results_summary')
    if 'methods_summary' in columns:
        op.drop_column('papers', 'methods_summary')
    if 'introduction_summary' in columns:
        op.drop_column('papers', 'introduction_summary')