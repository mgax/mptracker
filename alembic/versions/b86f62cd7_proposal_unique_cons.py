revision = 'b86f62cd7'
down_revision = '15510019a39'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_unique_constraint('proposal_unique_cdeppk_cdep_key',
                                'proposal', ['cdeppk_cdep'])
    op.create_unique_constraint('proposal_unique_cdeppk_senate_key',
                                'proposal', ['cdeppk_senate'])


def downgrade():
    op.drop_constraint('proposal_unique_cdeppk_senate_key', 'proposal')
    op.drop_constraint('proposal_unique_cdeppk_cdep_key', 'proposal')
