revision = '346102165a4'
down_revision = '5ae64c689b2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_unique_constraint('meta_unique_object_id_key',
                                'meta', ['object_id', 'key'])
    op.create_index('meta_object_id_index', 'meta', ['object_id'])


def downgrade():
    op.drop_index('meta_object_id_index')
    op.drop_constraint('meta_unique_objectid_key', 'meta')
