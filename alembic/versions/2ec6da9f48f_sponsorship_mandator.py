revision = '2ec6da9f48f'
down_revision = '5431ccea833'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column('sponsorship', 'person_id',
               existing_type=postgresql.UUID(),
               nullable=False)
    op.alter_column('sponsorship', 'proposal_id',
               existing_type=postgresql.UUID(),
               nullable=False)


def downgrade():
    op.alter_column('sponsorship', 'proposal_id',
               existing_type=postgresql.UUID(),
               nullable=True)
    op.alter_column('sponsorship', 'person_id',
               existing_type=postgresql.UUID(),
               nullable=True)
