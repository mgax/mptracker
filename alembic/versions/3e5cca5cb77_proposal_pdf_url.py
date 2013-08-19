revision = '3e5cca5cb77'
down_revision = '3648e45fb93'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal',
        sa.Column('pdf_url', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('proposal', 'pdf_url')
