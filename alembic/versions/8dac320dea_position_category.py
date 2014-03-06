revision = '8dac320dea'
down_revision = 'fa1b4442dc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('position', sa.Column('category', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('position', 'category')
