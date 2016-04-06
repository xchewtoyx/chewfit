'tool to pull weight data from google fit'
import argparse
import json
import os
import time

from apiclient.discovery import build
import httplib2
from oauth2client import client
from oauth2client.file import Storage
from oauth2client import tools
from six.moves.urllib.error import HTTPError


class FitClient(object):
    'Client class for googlefit api.'
    def __init__(self, args):
        self.args = args
        self.storage_path = os.path.join(os.environ['HOME'], '.chewfit')
        self.scope = 'https://www.googleapis.com/auth/fitness.body.read'

    @property
    def client_secrets(self):
        'retrieve oauth secrets from storage'
        secrets_path = os.path.join(self.storage_path, 'client_secrets.json')
        with open(secrets_path) as secrets_file:
            client_secret_data = json.load(secrets_file)
        return client_secret_data.get('installed')

    @property
    def credential_store(self):
        'retrieve oauth credential store'
        storage_path = os.path.join(self.storage_path, 'oauth_credentials')
        return Storage(storage_path)

    def client(self):
        'build api client'
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
        'bind to api service'
        return build('fitness', 'v1', http=self.client())

    def list_streams(self):
        'list available data streams'
        data_sources = self.service().users().dataSources()
        streams = data_sources.list(userId='me').execute()
        for stream in streams['dataSource']:
            print stream['dataStreamId']

    def merged_weights(self, start, stop):
        'fetch merged weight dataset'
        data_sets = self.service().users().dataSources().datasets()
        history = data_sets.get(
            dataSourceId=(
                'derived:com.google.weight:com.google.android.gms:merge_weight'
                ),
            datasetId='%d000000000-%d000000000' % (
                start,
                stop, ),
            userId='me').execute()
        data_points = history.get('point', [])
        return data_points


def run():
    'fetch datapoints and calculate moving average'
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument(
        '--offset', '-o', type=int, help='when to stop', default=0)
    parser.add_argument(
        '--window', '-w', type=int, help='days to average over',
        default=7)
    day_secs = 86400
    args = parser.parse_args()
    now = time.time() - args.offset * day_secs
    then = now - args.window * day_secs
    api_client = FitClient(args)
    try:
        data_points = api_client.merged_weights(then, now)
    except HTTPError:
        data_points = []
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
