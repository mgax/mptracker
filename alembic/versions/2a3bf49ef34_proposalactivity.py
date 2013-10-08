revision = '2a3bf49ef34'
down_revision = '25d765ee53b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('proposal_activity_item',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('html', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.Column('proposal_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('proposal_activity_item')
