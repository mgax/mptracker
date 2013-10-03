revision = '22f80ee91db'
down_revision = '5994be361ba'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal',
        sa.Column('cdeppk_cdep', sa.Integer(), nullable=True))
    op.add_column('proposal',
        sa.Column('cdeppk_senate', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('proposal', 'cdeppk_senate')
    op.drop_column('proposal', 'cdeppk_cdep')
