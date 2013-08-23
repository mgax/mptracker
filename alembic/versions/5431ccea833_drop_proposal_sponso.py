revision = '5431ccea833'
down_revision = '43dd72d2078'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('proposal', 'sponsored_by')


def downgrade():
    op.add_column('proposal',
        sa.Column('sponsored_by', sa.TEXT(), nullable=True))
