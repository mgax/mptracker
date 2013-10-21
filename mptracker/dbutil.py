import psycopg2.extensions
from datetime import date
import sqlalchemy.types
from flask import json


class JsonString(sqlalchemy.types.TypeDecorator):

    impl = sqlalchemy.types.Text

    def process_bind_param(self, value, dialect):
        return None if value is None else json.dumps(value)

    def process_result_value(self, value, dialect):
        return None if value is None else json.loads(value)


class InfDateAdapter:
    _adapter_registered = False

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def getquoted(self):
        if self.wrapped == date.max:
            return b"'infinity'::date"
        elif self.wrapped == date.min:
            return b"'-infinity'::date"
        else:
            return psycopg2.extensions.DateFromPy(self.wrapped).getquoted()


def register_infinity_adapter():
    psycopg2.extensions.register_adapter(date, InfDateAdapter)
    InfDateAdapter._adapter_registered = True
