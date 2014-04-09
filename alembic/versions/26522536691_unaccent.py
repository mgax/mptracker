revision = '26522536691'
down_revision = '4af3d03dcf7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "unaccent";')


def downgrade():
    op.execute('DROP EXTENSION IF EXISTS "unaccent";')
