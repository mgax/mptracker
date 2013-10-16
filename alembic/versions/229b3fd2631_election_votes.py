revision = '229b3fd2631'
down_revision = '2a3bf49ef34'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('mandate', 'votes', new_column_name='election_votes')
    op.alter_column('mandate', 'votes_percent',
                    new_column_name='election_votes_percent')


def downgrade():
    op.alter_column('mandate', 'election_votes_percent',
                    new_column_name='votes_percent')
    op.alter_column('mandate', 'election_votes', new_column_name='votes')
