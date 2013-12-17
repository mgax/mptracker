revision = '9bdc85383'
down_revision = '1adf695b50e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('group_vote',
        sa.Column('loyal_to_cabinet', sa.Boolean(), nullable=True))
    op.add_column('vote',
        sa.Column('loyal_to_cabinet', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('vote', 'loyal_to_cabinet')
    op.drop_column('group_vote', 'loyal_to_cabinet')
