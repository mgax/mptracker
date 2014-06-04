revision = '15510019a39'
down_revision = '18be3a9d7a1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mp_group',
        sa.Column('description', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('mp_group', 'description')
