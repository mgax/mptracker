from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from mptracker import models


class QuestionView(ModelView):

    column_searchable_list = ['title']


admin = Admin(name="MP Tracker")
admin.add_view(ModelView(models.Person, models.db.session))
admin.add_view(QuestionView(models.Question, models.db.session))
admin.add_view(ModelView(models.StenoChapter, models.db.session))
admin.add_view(ModelView(models.StenoParagraph, models.db.session))
