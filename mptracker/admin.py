from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from mptracker import models


admin = Admin(name="MP Tracker")
admin.add_view(ModelView(models.Person, models.db.session))
admin.add_view(ModelView(models.Question, models.db.session))
