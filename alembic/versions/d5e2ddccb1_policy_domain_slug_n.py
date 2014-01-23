revision = 'd5e2ddccb1'
down_revision = '15499993931'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('policy_domain', 'slug',
               existing_type=sa.TEXT(),
               nullable=False)


def downgrade():
    op.alter_column('policy_domain', 'slug',
               existing_type=sa.TEXT(),
               nullable=True)
