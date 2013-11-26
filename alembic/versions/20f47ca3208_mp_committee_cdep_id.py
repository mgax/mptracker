revision = '20f47ca3208'
down_revision = '5061ea76a8a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mp_committee',
        sa.Column('cdep_id', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column('mp_committee', 'cdep_id')
