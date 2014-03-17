revision = '3abf407e34a'
down_revision = '3a2359f421b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mp_group', sa.Column('year', sa.Integer(), nullable=True))
    op.execute("UPDATE mp_group SET year = 2012")


def downgrade():
    op.drop_column('mp_group', 'year')
