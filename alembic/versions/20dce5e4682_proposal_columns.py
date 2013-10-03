revision = '20dce5e4682'
down_revision = '4892e1511b9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal',
        sa.Column('date', sa.Date(), nullable=True))
    op.add_column('proposal',
        sa.Column('number_bpi', sa.Text(), nullable=True))
    op.add_column('proposal',
        sa.Column('number_cdep', sa.Text(), nullable=True))
    op.add_column('proposal',
        sa.Column('number_senate', sa.Text(), nullable=True))
    op.drop_column('proposal', 'cdep_serial')


def downgrade():
    op.add_column('proposal',
        sa.Column('cdep_serial', sa.Text(), nullable=True))
    op.drop_column('proposal', 'number_senate')
    op.drop_column('proposal', 'number_cdep')
    op.drop_column('proposal', 'number_bpi')
    op.drop_column('proposal', 'date')
