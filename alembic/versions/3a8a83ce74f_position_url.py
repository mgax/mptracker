revision = '3a8a83ce74f'
down_revision = '5272ded7959'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('position', sa.Column('url', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('position', 'url')
