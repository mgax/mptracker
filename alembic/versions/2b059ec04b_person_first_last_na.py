revision = '2b059ec04b'
down_revision = '3a8a83ce74f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('person', sa.Column('first_name', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('last_name', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('person', 'last_name')
    op.drop_column('person', 'first_name')
