revision = '3216a0bd78a'
down_revision = '49ed2a435cf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('mp_group', 'description')


def downgrade():
    op.add_column('mp_group', sa.Column('description', sa.TEXT(), nullable=True))
