revision = '561a34e43dc'
down_revision = '2205b132d84'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('person', sa.Column('slug', sa.Text(), nullable=True))
    op.create_unique_constraint('person_unique_slug', 'person', ['slug'])

    from mptracker.common import generate_slug
    used = set()
    conn = op.get_bind()
    for id, name in list(conn.execute("SELECT id, name FROM person")):
        slug = generate_slug(name, lambda v: v not in used)
        conn.execute("UPDATE person SET slug=%s WHERE id=%s", slug, id)
        used.add(slug)

    op.alter_column('person', 'slug', nullable=False)


def downgrade():
    op.drop_column('person', 'slug')
