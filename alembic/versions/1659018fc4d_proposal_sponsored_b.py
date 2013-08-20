revision = '1659018fc4d'
down_revision = '29ec835a8f5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal',
        sa.Column('sponsored_by', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('proposal', 'sponsored_by')
