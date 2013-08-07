revision = '434e742a7f1'
down_revision = '45ba5b8f7c3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('county',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('person',
        sa.Column('county_id', sa.CHAR(length=32), nullable=True),
    )


def downgrade():
    op.drop_column('person', 'county_id')
    op.drop_table('county')
