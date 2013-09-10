revision = '40132825652'
down_revision = '4097cd576be'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mp_group',
        sa.Column('short_name', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('mp_group', 'short_name')
