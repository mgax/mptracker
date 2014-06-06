revision = 'b86f62cd7'
down_revision = '15510019a39'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_unique_constraint('proposal_unique_cdeppk_cdep_key',
                                'proposal', ['cdeppk_cdep'])
    op.create_unique_constraint('proposal_unique_cdeppk_senate_key',
                                'proposal', ['cdeppk_senate'])
    op.create_unique_constraint('proposal_unique_number_cdep_key',
                                'proposal', ['number_cdep'])
    op.create_unique_constraint('proposal_unique_number_senate_key',
                                'proposal', ['number_senate'])
    op.create_unique_constraint('proposal_unique_number_bpi_key',
                                'proposal', ['number_bpi'])


def downgrade():
    op.drop_constraint('proposal_unique_number_bpi_key', 'proposal')
    op.drop_constraint('proposal_unique_number_senate_key', 'proposal')
    op.drop_constraint('proposal_unique_number_cdep_key', 'proposal')
    op.drop_constraint('proposal_unique_cdeppk_senate_key', 'proposal')
    op.drop_constraint('proposal_unique_cdeppk_cdep_key', 'proposal')
