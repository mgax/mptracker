revision = '3a5bbf74764'
down_revision = '2b7972a5d85'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('mandate',
        sa.Column('interval', postgresql.DATERANGE(), nullable=True))


def downgrade():
    op.drop_column('mandate', 'interval')
