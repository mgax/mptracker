revision = '4097cd576be'
down_revision = '22cfd89dfd7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mandate',
        sa.Column('candidate_party', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('mandate', 'candidate_party')
