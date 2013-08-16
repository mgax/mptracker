revision = '38579825699'
down_revision = '4bc50a6cca9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('person',
        sa.Column('minority', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('person', 'minority')
