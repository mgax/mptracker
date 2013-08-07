revision = 'b0a6720166'
down_revision = '434e742a7f1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('county',
        sa.Column('geonames_code', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column('county', 'geonames_code')
