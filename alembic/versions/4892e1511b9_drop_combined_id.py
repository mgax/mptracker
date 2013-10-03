revision = '4892e1511b9'
down_revision = '22f80ee91db'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('proposal', 'combined_id')


def downgrade():
    op.add_column('proposal',
        sa.Column('combined_id', sa.TEXT(), nullable=True))
