revision = '17964fe11d0'
down_revision = '16de00f8ecc'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('question',
        sa.Column('policy_domain_id', postgresql.UUID(), nullable=True))
    op.create_foreign_key(
        'policy_domain_id_fkey',
        'question', 'policy_domain',
        ['policy_domain_id'], ['id'],
    )


def downgrade():
    op.drop_column('question', 'policy_domain_id')
