from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from mptracker import models
from mptracker.auth import is_privileged

admin = Admin(name="MP Tracker")


class AuthView(ModelView):

    can_create = False
    can_edit = False
    can_delete = False

    def is_accessible(self):
        return is_privileged()

admin.add_view(AuthView(models.StenoChapter, models.db.session))
admin.add_view(AuthView(models.StenoParagraph, models.db.session))
admin.add_view(AuthView(models.User, models.db.session))
admin.add_view(AuthView(models.County, models.db.session))
admin.add_view(AuthView(models.CommitteeSummary, models.db.session))


class PersonView(AuthView):

    column_searchable_list = ['name']

admin.add_view(PersonView(models.Person, models.db.session))


class QuestionView(AuthView):

    column_searchable_list = ['title', 'text']
    list_template = 'questions/admin_list.html'

admin.add_view(QuestionView(models.Question, models.db.session))
