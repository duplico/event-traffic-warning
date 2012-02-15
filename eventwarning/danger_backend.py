import eventful as eventful_api
import foursquare
from datetime import date
import pylast
import pprint
import operator
from api_keys import *
import songkick

VERBOSE = True

class EventStruct:
    title = None
    eventful_event = None
    time = None
    venue = None
    venue_capacity = 0
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

    def get_lfm_plays(self):
        return reduce(operator.add, (
            lfm_performer.get_playcount() \
                for lfm_performer in self.lfm_performers
        ), 0)

    def get_eventful_demands(self):
        return reduce(operator.add, (
            int(eventful_performer['demand_member_count']) \
                for eventful_performer in self.eventful_performers
        ), 0)

    def get_attendance_estimate(self):
        # If we don't know the capacity, we'll assume it's bar sized.
        # Otherwise we'll need to fix the venue on songkick.
        capacity = self.venue_capacity or 100
        lfm_plays = self.get_lfm_plays()
        attendance_possible = lfm_plays / 500.0
        # Also there should probably be a venue size penalty
        attendance = min(capacity, attendance_possible)
        return attendance

    def venue_capacity_estimated(self):
        return not bool(self.venue_capacity)



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

    # Initialize Songkick API:
    sk = songkick.SongkickAPI(SK_KEY)

    page_number = 0
    max_pages = 1
    while page_number < max_pages:
        page_number += 1
        events = eventful.call('/events/search', q='music', l='74103',
                          date=eventful_daterange, page_number=page_number)
        if events['total_items'] == '0':
            return []
        max_pages = int(events['page_count'])

        event_list = events['events']['event']
        if type(event_list) != list:
            event_list = [event_list]

        for event in event_list:
            venue_title = event['venue_name'].replace(u'\u2019', "'")
            venue_title = venue_title.encode('ascii', 'ignore')
            venue_coords = '%s,%s' % (event['latitude'], event['longitude'])
            venue_city = event['city_name']
            if VERBOSE: print 'Producing an event record for the event titled "%s" at "%s":' % (event['title'], venue_title)
            if VERBOSE: print '\tEventful venue is called "%s", attempting to normalize with Foursquare and Songkick' % venue_title

            venue_guess = None
            # TODO: we definitely need to normalize venues using foursquare
            ## For some reason the foursquare support is broken on my machine
            ##  due to some kind of httplib2 timeout weirdness that I don't
            ##  care to diagnose at the moment. The issue is:
            ##  <http://code.google.com/p/python-rest-client/issues/detail?id=1>
            #
            venues = fsq.venues.search(params=dict(
                    query=venue_title,
                    ll=venue_coords,
                    intent='match'
                )
            ) # TODO: we're matching the second stage here. :(
            fsq_venue_guess = venues['venues'][0]
            checkins = fsq_venue_guess['hereNow']['count']
            venue_guess = fsq_venue_guess['name']
            if VERBOSE: print '\t\tFoursquare venue "%s" found' % venue_guess

            # Try to grab the capacity of the venue from Songkick:
            sk_venue_guess = None
            sk_venues_guess = sk.venue_search('%s %s' % (
                venue_guess or venue_title,
                venue_city
            ))
            sk_capacity = 0 # Unknown
            if sk_venues_guess:
                sk_venue_guess = sk_venues_guess['venue'][0]
                sk_capacity = sk_venue_guess['capacity']
                if VERBOSE: print '\t\tSongkick venue "%s" found' % sk_venue_guess['displayName']
                if VERBOSE: print '\t\tSongkick venue capacity %s' % str(sk_capacity)

            event_struct = EventStruct(
                title=event['title'],
                time=event['start_time'],
                venue=venue_title,
                eventful_event=event,
                venue_capacity=sk_capacity or 0,
                fsq_venue=fsq_venue_guess,
                sk_venue=sk_venue_guess,
            )

            ret_events.append(event_struct)
            if VERBOSE: print '\tLooking for performers:'
            performers = event['performers']
            if performers:
                performer = performers['performer']
                if type(performer) == dict:
                    performer = [performer]
                # performer is a list:
                playcounts = []
                for perf in performer:
                    performer_name = perf['name']
                    if VERBOSE: print '\t\tFound performer "%s"' % performer_name
                    # Grab last.fm's first result for this artist:
                    lfm_search = lfm.search_for_artist(performer_name)
                    lfm_performer = lfm_search.get_next_page()[0]
                    # Grab eventful's data for this performer:
                    eventful_performer = eventful.call('/performers/get', id=perf['id'])
                    # Store it:
                    event_struct.performers.append(performer_name)
                    event_struct.lfm_performers.append(lfm_performer)
                    event_struct.eventful_performers.append(eventful_performer)
                    if VERBOSE: print '\t\tLast.fm performer: "%s" (%i)' % (lfm_performer.name, lfm_performer.get_playcount())
    ret_events.sort(key=lambda a: a.venue)
    ret_events.sort(key=lambda a: a.venue_capacity)
    return ret_events

def attendance_for_events(events):
    attendance_total = 0
    for event in events:
        attendance_total += event.get_attendance_estimate()
    return attendance_total

def attendance_for_day(day):
    events = get_events_for_day(day)
    return attendance_for_events(events)

def print_day_summary(day):
    events = get_events_for_day(day)
    day_lfm_plays = 0
    day_eventful_demands = 0

    for event in events:
        event_lfm_plays = event.get_lfm_plays()
        event_eventful_demands = event.get_eventful_demands()

        event_desc = '%s at %s (lfm:%i, eventful:%i, cap:%s): %i' % (
            event.title,
            event.venue,
            event_lfm_plays,
            event_eventful_demands,
            str(event.venue_capacity or '?'),
            event.get_attendance_estimate(),
        )
        print event_desc
    print 'Total estimate: %i' % attendance_for_events(events)

def prioritize_events(events):
    out_events = dict(useful=[], useless=[])
    out_needs_info = []
    for event in events:
        if not event.performers:
            out_events['useless'].append(event)
        else:
            out_events['useful'].append(event)
        if not event.venue_capacity:
            out_needs_info.append(event) # TODO: refactor
    return out_events

def prioritized_events_for_day(day):
    return prioritize_events(get_events_for_day(day))
