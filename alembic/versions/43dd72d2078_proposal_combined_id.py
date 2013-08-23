revision = '43dd72d2078'
down_revision = '4d74b4b0d3e'

from alembic import op
import sqlalchemy as sa



def upgrade():
    op.add_column('proposal',
        sa.Column('combined_id', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('proposal', 'combined_id')
