revision = '3f541c42af6'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('question', sa.Column('addressee', sa.String(), nullable=True))
    op.add_column('question', sa.Column('type', sa.String(), nullable=True))


def downgrade():
    op.drop_column('question', 'type')
    op.drop_column('question', 'addressee')
