revision = '2dc81b310cf'
down_revision = '355ed1e03db'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('proposal',
        sa.Column('decision_chamber_id', postgresql.UUID(), nullable=True))


def downgrade():
    op.drop_column('proposal', 'decision_chamber_id')
