revision = '1b8378b8914'
down_revision = '32590709513'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('person', 
            sa.Column('romania_curata', sa.Text(), nullable=True))
    

def downgrade():
    op.drop_column('person', 'romania_curata')
