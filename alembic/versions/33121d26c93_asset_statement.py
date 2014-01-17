revision = '33121d26c93'
down_revision = '2b059ec04b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('asset_statement',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('raw_data', sa.Text(), nullable=True),
        sa.Column('land_agri_area', sa.Integer(), nullable=True),
        sa.Column('land_city_area', sa.Integer(), nullable=True),
        sa.Column('net_worth_eur', sa.Integer(), nullable=True),
        sa.Column('realty_count', sa.Integer(), nullable=True),
        sa.Column('vehicle_count', sa.Integer(), nullable=True),
        sa.Column('year_income_eur', sa.Integer(), nullable=True),
        sa.Column('person_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['person.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('asset_statement')
