import eventful as eventful_api
import foursquare
from datetime import date
import pylast
import pprint
import operator
import api_keys

class EventStruct:
    title = None
    eventful_event = None
    time = None
    venue = None
    fsq_venue = None
    performers = []
    lfm_performers = []
    eventful_performers = []
    
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)        
        self.performers = []
        self.lfm_performers = []
        self.eventful_performers = []

def get_events_for_day(day):
    ret_events = []
    # Initialize eventful API:
    eventful = eventful_api.API('mtFH6X2rLdv7MGZX')
    eventful_date = day.strftime('%Y%m%d00')
    eventful_daterange = '%s-%s' % (eventful_date, eventful_date)
    
    # Initialize Last.fm API:
    lfm = pylast.LastFMNetwork(api_key=LFM_KEY, api_secret=LFM_SEC)
    
    # Initialize Foursquare API (userless):
    fsq = foursquare.Foursquare(client_id=FSQ_CID, client_secret=FSQ_SEC)
    
    page_number = 0
    max_pages = 1
    while page_number < max_pages:
        page_number += 1
        events = eventful.call('/events/search', q='music', l='74103', 
                          date=eventful_daterange, page_number=page_number)
        max_pages = int(events['page_count'])
        
        event_list = events['events']['event']
        if type(event_list) != list:
            event_list = [event_list]

        for event in event_list:
            venue_title = event['venue_name'].replace(u'\u2019', "'")
            venue_title = venue_title.encode('ascii', 'ignore')
            venue_coords = '%s,%s' % (event['latitude'], event['longitude'])
            venues = fsq.venues.search(params=dict(
                    query=venue_title,
                    ll=venue_coords,
                    intent='match'
                )
            )
            venue_guess = venues['venues'][0]
            checkins = venue_guess['hereNow']['count']
            
            event_struct = EventStruct(
                title=event['title'],
                time=event['start_time'],
                venue=venue_title,
                eventful_event=event,
                fsq_venue=venue_guess
            )
            
            ret_events.append(event_struct)
            
            performers = event['performers']
            if performers:
                performer = performers['performer']
                if type(performer) == dict:
                    performer = [performer]
                # performer is a list:
                playcounts = []
                for perf in performer:
                    performer_name = perf['name']
                    # Grab last.fm's first result for this artist:
                    lfm_search = lfm.search_for_artist(performer_name)
                    lfm_performer = lfm_search.get_next_page()[0]
                    # Grab eventful's data for this performer:
                    eventful_performer = eventful.call('/performers/get', id=perf['id'])
                    # Store it:
                    event_struct.performers.append(performer_name)
                    event_struct.lfm_performers.append(lfm_performer)
                    event_struct.eventful_performers.append(eventful_performer)
    # TODO: sort by venue size, when that's available
    ret_events.sort(key=lambda a: a.venue)
    return ret_events
    

def danger_for_day(day):
    events = get_events_for_day(day)
    day_lfm_plays = 0
    day_eventful_demands = 0
    
    for event in events:
        event_lfm_plays = 0
        for lfm_performer in event.lfm_performers:
            event_lfm_plays += lfm_performer.get_playcount()
        
        event_eventful_demands = 0
        for eventful_performer in event.eventful_performers:
            event_eventful_demands += int(eventful_performer['demand_member_count'])
        
        event_desc = '%s at %s (lfm:%i, eventful:%i)' % (
            event.title,
            event.venue,
            event_lfm_plays,
            event_eventful_demands,
        )
        print event_desc
        day_lfm_plays += event_lfm_plays
        day_eventful_demands += event_eventful_demands
    return day_lfm_plays