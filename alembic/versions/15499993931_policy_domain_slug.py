revision = '15499993931'
down_revision = '33121d26c93'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('policy_domain',
        sa.Column('slug', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('policy_domain', 'slug')
