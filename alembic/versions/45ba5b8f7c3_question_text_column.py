revision = '45ba5b8f7c3'
down_revision = '3f541c42af6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('question', sa.Column('text', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('question', 'text')
