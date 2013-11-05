revision = 'b9e0fdc1c7'
down_revision = '1ae5bbf1e02'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('voting_session',
        sa.Column('final', sa.Boolean(), nullable=True))
    op.execute('UPDATE voting_session SET final = false')
    op.alter_column('voting_session', 'final', nullable=False)


def downgrade():
    op.drop_column('voting_session', 'final')
