revision = '3de03f8b089'
down_revision = '4d73f8e17e0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mp_committee',
        sa.Column('chamber_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('mp_committee', 'chamber_id')
