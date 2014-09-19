def get_text(ns, name):
    assert ns == 'general'
    import flask
    return flask.render_template('text_%s.html' % name)
