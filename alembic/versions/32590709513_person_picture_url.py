revision = '32590709513'
down_revision = '17964fe11d0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mandate',
                  sa.Column('picture_url', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('mandate', 'picture_url')
