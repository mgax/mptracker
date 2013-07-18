import uuid
from flask.ext.sqlalchemy import SQLAlchemy

def uuid_column():
    return db.Column(db.CHAR(32), primary_key=True,
                     default=lambda: str(uuid.uuid4()))


db = SQLAlchemy()


class Person(db.Model):
    id = uuid_column()
    name = db.Column(db.String)
    cdep_id = db.Column(db.Integer)
