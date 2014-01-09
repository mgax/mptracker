revision = '2205b132d84'
down_revision = '9bdc85383'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('voting_session',
        sa.Column('cabinet_choice', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('voting_session', 'cabinet_choice')
