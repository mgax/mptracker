revision = '355ed1e03db'
down_revision = '2ec6da9f48f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('chamber',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('slug', sa.Text(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    chamber = sql.table('chamber', sql.column('id'),
                                   sql.column('slug'),
                                   sql.column('name'))
    op.execute(
        chamber.insert().values([
            {'id': 'eef32a11-edb4-4ed4-a943-ebfb42f59c8c',
             'slug': 'cdep',
             'name': "Camera Deputaților"},
            {'id': 'b1b9f6a4-b472-404d-b222-6d0d04dbf3b9',
             'slug': 'senat',
             'name': "Senat"},
        ]))


def downgrade():
    op.drop_table('chamber')
