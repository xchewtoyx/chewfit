import argparse 
import json
import os
import sys
import time

from apiclient.discovery import build
import httplib2
from oauth2client import client
from oauth2client.file import Storage
from oauth2client import tools

class FitClient(object):
    def __init__(self, args):
        self.args = args
        self.storage_path = os.path.join(os.environ['HOME'], '.chewfit')
        self.scope = 'https://www.googleapis.com/auth/fitness.body.read'

    @property
    def client_secrets(self):
        secrets_path = os.path.join(self.storage_path, 'client_secrets.json')
        with open(secrets_path) as secrets_file:
            client_secret_data = json.load(secrets_file)
        return client_secret_data.get('installed')

    @property
    def credential_store(self):
        storage_path = os.path.join(self.storage_path, 'oauth_credentials')
        return Storage(storage_path)

    def client(self):
        http_client = httplib2.Http()
        credentials = self.credential_store.get()
        if not credentials or credentials.invalid:
            flow = client.OAuth2WebServerFlow(
                client_id=self.client_secrets['client_id'],
                client_secret=self.client_secrets['client_secret'],
                scope=self.scope,
                user_agent="chewfit/0.1",
                redirect_url="urn:ietf:wg:oauth:2.0:oob",
            )
            tools.run_flow(flow, self.credential_store, self.args)
        # The older gdata api needs the oauth token to be converted
        self.credential_store.get().authorize(http_client)
        return http_client

    def service(self):
        return build('fitness', 'v1', http=self.client())

def run():
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument(
        '--offset', '-o', type=int, help='when to stop', default=0)
    parser.add_argument(
        '--window', '-w', type=int, help='days to average over', 
        default=7)
    day_secs = 86400
    args = parser.parse_args()
    client = FitClient(args)
    service = client.service()
    ds= service.users().dataSources().datasets()
    now = time.time() - args.offset * day_secs
    then = now - args.window * day_secs
    history = ds.get(
        dataSourceId=(
            'raw:com.google.weight:com.google.android.apps.fitness:user_input'
            ),
        datasetId='%d000000000-%d000000000' % (
            then,
            now, ),
        userId='me').execute()
    data_points = history.get('point', [])
    if data_points:
        total = sum(point['value'][0]['fpVal'] for point in data_points)
        count = len(data_points)
        mean = total / count
        point = [{
            'name': 'weight_%dd' % (args.window,),
            'columns': ['time', 'weight', 'points'],
            'points': [
                [now*1000, mean, count],
                ],
            }]
        print json.dumps(point)


if __name__ == '__main__':
    run()
