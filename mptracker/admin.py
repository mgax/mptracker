from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from mptracker import models
from mptracker.auth import is_privileged


class AuthView(ModelView):

    can_create = False
    can_edit = False
    can_delete = False

    def is_accessible(self):
        return is_privileged()


class QuestionView(AuthView):

    column_searchable_list = ['title']


admin = Admin(name="MP Tracker")
admin.add_view(AuthView(models.Person, models.db.session))
admin.add_view(QuestionView(models.Question, models.db.session))
admin.add_view(AuthView(models.StenoChapter, models.db.session))
admin.add_view(AuthView(models.StenoParagraph, models.db.session))
admin.add_view(AuthView(models.User, models.db.session))
