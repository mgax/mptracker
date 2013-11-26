revision = '1872f4529b3'
down_revision = '3de03f8b089'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('policy_domain',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('mp_committee',
        sa.Column('policy_domain_id', postgresql.UUID(), nullable=True),
    )
    op.create_foreign_key(
        'policy_domain_id_fkey',
        'mp_committee', 'policy_domain',
        ['policy_domain_id'], ['id'],
    )
    op.create_table('ministry',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('policy_domain_id', postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['policy_domain_id'], ['policy_domain.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('ministry')
    op.drop_column('mp_committee', 'policy_domain_id')
    op.drop_table('policy_domain')
