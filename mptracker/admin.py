import flask
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView as ModelView_base
from mptracker import models
from mptracker.auth import is_privileged

admin = Admin(name="MP Tracker")


class ModelView(ModelView_base):

    can_create = False
    can_edit = False
    can_delete = False

    list_template = 'admin_list.html'
    view_route = None

    def __init__(self, model, **kwargs):
        super().__init__(model, models.db.session)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def is_accessible(self):
        return is_privileged()

    def get_view_url(self, row):
        if self.view_route:
            (view_name, pk_name) = self.view_route.split(':')
            return flask.url_for(view_name, **{pk_name: row.id})

        else:
            return None


admin.add_view(ModelView(models.TranscriptChapter))
admin.add_view(ModelView(models.Transcript))
admin.add_view(ModelView(models.User))
admin.add_view(ModelView(models.County))
admin.add_view(ModelView(models.Proposal,
                         view_route='proposals.proposal:proposal_id'))
admin.add_view(ModelView(models.CommitteeSummary,
                         view_route='pages.committee_summary:summary_id'))
admin.add_view(ModelView(models.Question,
                         view_route='questions.question_detail:question_id'))
admin.add_view(ModelView(models.Person,
                         view_route='pages.person:person_id',
                         column_searchable_list=['name']))
admin.add_view(ModelView(models.Mandate,
                         column_searchable_list=['cdep_number']))
