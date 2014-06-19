revision = '4bed8dc91cc'
down_revision = '101109e1269'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal', sa.Column('activity', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('proposal', 'activity')
