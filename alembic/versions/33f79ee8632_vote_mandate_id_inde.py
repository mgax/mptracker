revision = '33f79ee8632'
down_revision = '3abf407e34a'

from alembic import op


def upgrade():
    op.create_index('vote_mandate_id_index', 'vote', ['mandate_id'])


def downgrade():
    op.drop_index('vote_mandate_id_index')
