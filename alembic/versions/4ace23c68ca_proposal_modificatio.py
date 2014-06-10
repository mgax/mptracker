revision = '4ace23c68ca'
down_revision = 'b86f62cd7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal',
        sa.Column('modification_date', sa.Date(), nullable=True))
    op.execute("UPDATE proposal SET modification_date = date")


def downgrade():
    op.drop_column('proposal', 'modification_date')
