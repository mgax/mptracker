revision = '4d74b4b0d3e'
down_revision = '197c7328f64'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.rename_table('sponsors', 'sponsorship')


def downgrade():
    op.rename_table('sponsorship', 'sponsors')
