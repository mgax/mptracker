from mptracker.models import Text, TextVersion


def get_text(ns, name):
    text = Text.query.filter_by(ns=ns, name=name).first()
    if text:
        version = text.versions.order_by(TextVersion.time.desc()).first()
        if version:
            return {
                'content': version.content,
                'more_content': version.more_content,
            }

    return {'content': "", 'more_content': ""}
