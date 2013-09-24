from alembic import context
from mptracker.models import db


context.configure(connection=db.session.connection(),
                  target_metadata=db.metadata)

context.run_migrations()

if not context.is_offline_mode():
    db.session.commit()
