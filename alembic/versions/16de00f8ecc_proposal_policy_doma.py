revision = '16de00f8ecc'
down_revision = '1872f4529b3'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('proposal',
        sa.Column('policy_domain_id', postgresql.UUID(), nullable=True))
    op.create_foreign_key(
        'policy_domain_id_fkey',
        'proposal', 'policy_domain',
        ['policy_domain_id'], ['id'],
    )


def downgrade():
    op.drop_column('proposal', 'policy_domain_id')
