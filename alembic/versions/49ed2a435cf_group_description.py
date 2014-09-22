revision = '49ed2a435cf'
down_revision = '5927719682b'

import uuid
from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql
import jinja2


def random_uuid():
    return str(uuid.uuid4())


def upgrade():
    text = sql.table('text',
        sql.column('id'),
        sql.column('ns'),
        sql.column('name'),
    )
    text_version = sql.table( 'text_version',
        sql.column('id'),
        sql.column('text_id'),
        sql.column('time'),
        sql.column('content'),
        sql.column('more_content'),
    )
    time = datetime(2014, 9, 22, 11, 50, 0)

    conn = op.get_bind()
    query = (
        "SELECT short_name, description FROM mp_group "
        "WHERE year=2012 "
        "AND description IS NOT NULL"
    )
    data = list(conn.execute(query))

    for name, description in data:
        text_id = random_uuid()
        content = (
            jinja2.Markup('<p><strong>%s</strong> %s</p>')
            % (name, description)
        )
        op.execute(text.insert().values({
            'id': text_id,
            'ns': 'party',
            'name': name,
        }))
        op.execute(text_version.insert().values({
            'id': random_uuid(),
            'text_id': text_id,
            'time': time,
            'content': content,
            'more_content': '',
        }))


def downgrade():
    op.execute(
        "DELETE FROM text_version "
        "WHERE text_id IN (SELECT id FROM text WHERE ns = 'party')"
    )
    op.execute("DELETE FROM text WHERE ns = 'party'")
