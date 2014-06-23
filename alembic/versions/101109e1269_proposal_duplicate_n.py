revision = '101109e1269'
down_revision = '433d8997b7d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint('proposal_unique_number_senate_key', 'proposal')
    op.drop_constraint('proposal_unique_number_cdep_key', 'proposal')
    op.drop_constraint('proposal_unique_number_bpi_key', 'proposal')


def downgrade():
    op.create_unique_constraint('proposal_unique_number_bpi_key',
                                'proposal', ['number_bpi'])
    op.create_unique_constraint('proposal_unique_number_cdep_key',
                                'proposal', ['number_cdep'])
    op.create_unique_constraint('proposal_unique_number_senate_key',
                                'proposal', ['number_senate'])
