from restful_lib import Connection
import json

class SongkickAPI(object):
    def __init__(self, api_key):
        self.api_key = api_key
        self.connection = Connection('http://api.songkick.com/api/3.0/')

    def venue_search(self, query, page=1):
        return self._get('/search/venues.json',
                         params=dict(query=query, page=page))

    def location_search(self, name=None, location=None):
        raise NotImplementedError

    def artist_search(self, name=None):
        raise NotImplementedError

    def event_search(self, artist_name=None, location=None, min_date=None,
                     max_date=None):
        raise NotImplementedError

    def _get(self, resource, params={}):
        params.update(apikey=self.api_key, page=2)
        query_result = self.connection.request_get(resource, args=params)
        object_result = json.loads(query_result['body'])
        return object_result
