revision = '5ae64c689b2'
down_revision = '3a5bbf74764'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index('vote_voting_session_id_index',
                    'vote', ['voting_session_id'])


def downgrade():
    op.drop_index('vote_voting_session_id_index')
