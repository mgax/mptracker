revision = '29ec835a8f5'
down_revision = '191d638f4fb'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('sponsors',
        sa.Column('id', postgresql.UUID(), nullable=False))


def downgrade():
    op.drop_column('sponsors', 'id')
