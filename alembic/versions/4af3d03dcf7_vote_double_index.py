revision = '4af3d03dcf7'
down_revision = '33f79ee8632'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index(
        'vote_mandate_id_voting_session_id_index',
        'vote',
        ['mandate_id', 'voting_session_id'],
    )


def downgrade():
    op.drop_index('vote_mandate_id_voting_session_id_index')
