import requests
import flask
from werkzeug.urls import Href
from mptracker.scraper.common import GenericModel


class File(GenericModel):

    pass


def authorize():
    config = flask.current_app.config

    authorize_url = Href('https://accounts.google.com/o/oauth2/auth')({
        'response_type': 'code',
        'client_id': config['GDRIVE_CLIENT_ID'],
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'scope': ' '.join([
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly',
            'https://www.googleapis.com/auth/drive.appdata',
            'https://www.googleapis.com/auth/drive.apps.readonly',
        ]),
    })

    print('please visit:')
    print(authorize_url)
    code = input('code > ')

    resp = requests.post(
        'https://accounts.google.com/o/oauth2/token',
        data={
            'code': code,
            'client_id': config['GDRIVE_CLIENT_ID'],
            'client_secret': config['GDRIVE_CLIENT_SECRET'],
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'authorization_code',
        }
    )
    assert resp.status_code == 200
    print('GDRIVE_REFRESH_TOKEN = %r' % resp.json()['refresh_token'])


def get_access_token():
    config = flask.current_app.config

    resp = requests.post(
        'https://accounts.google.com/o/oauth2/token',
        data={
            'refresh_token': config['GDRIVE_REFRESH_TOKEN'],
            'client_id': config['GDRIVE_CLIENT_ID'],
            'client_secret': config['GDRIVE_CLIENT_SECRET'],
            'grant_type': 'refresh_token',
        }
    )
    assert resp.status_code == 200
    return resp.json()['access_token']


class PictureFolder:

    def __init__(self):
        self.token = get_access_token()


    def list(self, folder_key):
        resp = requests.get(
            'https://www.googleapis.com/drive/v2/files',
            params={
                'maxResults': 1000,
                'q': "'%s' in parents" % folder_key,
            },
            headers={
                'Authorization': 'Bearer ' + self.token,
            },
        )
        assert resp.status_code == 200

        latest = {}

        for item in resp.json()['items']:
            f = File(
                filename=item['title'],
                md5=item['md5Checksum'],
                url=item['downloadUrl'],
                modified=item['modifiedDate'],
            )

            if f.filename in latest:
                if latest[f.filename].modified > f.modified:
                    continue

            latest[f.filename] = f

        return (latest[k] for k in sorted(latest))


    def download(self, item, chunk_size=65536):
        resp = requests.get(
            item.url,
            stream=True,
            headers={
                'Authorization': 'Bearer ' + self.token,
            },
        )
        assert resp.status_code == 200

        try:
            yield from resp.iter_content(chunk_size)
        finally:
            resp.close()
