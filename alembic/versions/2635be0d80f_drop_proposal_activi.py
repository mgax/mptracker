revision = '2635be0d80f'
down_revision = '4bed8dc91cc'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_table('proposal_activity_item')


def downgrade():
    op.create_table(
        'proposal_activity_item',
        sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column('date', sa.DATE(), autoincrement=False, nullable=True),
        sa.Column('location', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('html', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('order', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('proposal_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], name='proposal_activity_item_proposal_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='proposal_activity_item_pkey'),
    )
