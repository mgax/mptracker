revision = '55c008192aa'
down_revision = 'c9230f65c6'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('controversy',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('slug', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.add_column('voting_session',
        sa.Column('controversy_id', postgresql.UUID(), nullable=True))
    op.create_foreign_key(
        'controversy_id_fkey',
        'voting_session', 'controversy',
        ['controversy_id'], ['id'],
    )


def downgrade():
    op.drop_column('voting_session', 'controversy_id')
    op.drop_table('controversy')
