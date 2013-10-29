revision = '1ae5bbf1e02'
down_revision = '346102165a4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('vote', sa.Column('loyal', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('vote', 'loyal')
