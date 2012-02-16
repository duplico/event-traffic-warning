from restful_lib import Connection
import json
import math
import pprint

class SongkickAPI(object):
    def __init__(self, api_key):
        self.api_key = api_key
        self.connection = Connection('http://api.songkick.com/api/3.0/')

    def venue_search(self, query):
        return self._get_list('/search/venues.json',
                         params=dict(query=query, page=page),
                         resource_type='venue')

    def venue_details(self, venue_id):
        return self._get_single(
            '/venues/%i.json' % venue_id,
            resource_type='venue'
        )

    def location_search(self, name=None, location=None):
        raise NotImplementedError

    def artist_search(self, name=None):
        raise NotImplementedError

    def event_search(self, artist_name=None, location=None, min_date=None,
                     max_date=None):
        assert location and min_date and max_date
        params = dict(location=location, min_date=min_date, max_date=max_date)
        if artist_name:
            params.update(artist_name=artist_name)
        return self._get_list('/events.json', params=params, resource_type='event')

    def _get(self, resource, params={}, resource_type='event'):
        params.update(apikey=self.api_key)
        query_result = self.connection.request_get(resource, args=params,
                                                   headers={'cache-control': 'no-cache'})
        object_result = json.loads(query_result['body'])['resultsPage']
        return object_result

    def _get_list(self, resource, params={}, resource_type='event'):
        pages = 1
        current_page = 0
        result = []

        while current_page < pages:
            params.update(page=current_page+1)
            current_page+=1
            object_result = self._get(resource, params=params,
                                      resource_type=resource_type)
            per_page = float(object_result['perPage'])
            tot_entries = int(object_result['totalEntries'])
            pages = int(math.ceil(tot_entries / per_page))
            if object_result['results']:
                result = result + object_result['results'][resource_type]
        return result

    def _get_single(self, resource, params={}, resource_type='event'):
        object_result = self._get(resource, params=params,
                                  resource_type=resource_type)
        if object_result['results']:
            result = object_result['results'][resource_type]
        else:
            result = None
        return result
