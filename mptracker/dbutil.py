import sqlalchemy.types
from flask import json


class JsonString(sqlalchemy.types.TypeDecorator):

    impl = sqlalchemy.types.Text

    def process_bind_param(self, value, dialect):
        return None if value is None else json.dumps(value)

    def process_result_value(self, value, dialect):
        return None if value is None else json.loads(value)
