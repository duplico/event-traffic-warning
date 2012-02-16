import eventful as eventful_api
import foursquare
from datetime import date
import pylast
import pprint
import operator
from api_keys import *
import songkick
import models
import flask

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

def get_sk_performer_list(event, fsq=None, lfm=None):
    if not fsq:
        fsq = foursquare.Foursquare(client_id=FSQ_CID, client_secret=FSQ_SEC)
    if not lfm:
        lfm = pylast.LastFMNetwork(api_key=LFM_KEY, api_secret=LFM_SEC)
    sk_performers = []
    performers = event['performance']
    for performer in performers:
        print performer['artist']['identifier']
        mbid = None
        if performer['artist']['identifier']: # TODO: handle longer than 1?
            assert len(performer['artist']['identifier'])==1
            mbid = performer['artist']['identifier'][0].get('mbid', None)

        lfm_performer = get_lfm_performer(
            mbid=mbid,
            name=performer['artist']['displayName'],
            lfm=lfm
        )
        sk_performers.append(lfm_performer)
    return sk_performers

def songkick_events_for_day(day, zip):
    sk = songkick.SongkickAPI(SK_KEY)
    loc_db = models.ZipCode.load('/locations/zip/%s' % zip)
    loc = 'geo:%s,%s' % (loc_db.lat, loc_db.lon)
    date = day.strftime('%Y-%m-%d')
    all_events = sk.event_search(location=loc, min_date=date, max_date=date)
    zip_events = []
    for event in all_events:
        venue = sk.venue_details(event['venue']['id'])
        if venue['zip'] == zip:
            zip_events.append((event, venue, get_sk_performer_list(event)))
    return zip_events

def get_foursquare_venue_normalization(sk_venue, fsq=None):
    if not fsq:
        fsq = foursquare.Foursquare(client_id=FSQ_CID, client_secret=FSQ_SEC)
    venue_url_sk = sk_venue['uri']

    # First try searching by songkick venue URL:
    venue_guesses = fsq.venues.search(params=dict(
        url=venue_url_sk
    ))['venues']

    # If we get any results, pick the first one:
    if venue_guesses:
        fsq_venue = venue_guesses[0]
    else:
        # TODO: We're going to need to get it some other way
        fsq_venue = None
        assert False # crash.

    return fsq_venue

def get_lfm_performer(mbid=None, name=None, lfm=None):
    if not lfm:
        lfm = pylast.LastFMNetwork(api_key=LFM_KEY, api_secret=LFM_SEC)
    assert mbid or name
    artist = None
    if mbid:
        artist = lfm.get_artist_by_mbid(mbid)
    if name and not mbid or not artist:
        artist = lfm.get_artist(name)
    artist_dict = {}
    if artist:
        artist_dict.update(
            name=artist.name,
            playcount=artist.get_playcount(),
            mbid=artist.get_mbid(),
            url=artist.get_url()
        )
    return artist_dict

def get_eventful_performer_list(lfm, event):
    raise NotImplementedError()

def get_events_for_day(day):
    ret_events = []

    # Initialize Songkick API:
    sk = songkick.SongkickAPI(SK_KEY)
    # Initialize Foursquare API (userless):
    fsq = foursquare.Foursquare(client_id=FSQ_CID, client_secret=FSQ_SEC)
    # Initialize Last.fm API:
    lfm = pylast.LastFMNetwork(api_key=LFM_KEY, api_secret=LFM_SEC)

    # Grab the day's events in the desired zip code:
    songkick_event_venues = songkick_events_for_day(day, '74103')

    # TODO: grab eventful's events for the same area/day
    # TODO: merge them

    event_venues = songkick_event_venues

    # Now, let's check out each event individually:
    for event, venue, performers in event_venues:
        event_name = event['displayName']
        venue_name = venue['displayName']
        venue_url_sk = venue['uri']
        venue_capacity = venue['capacity'] or 0
        if VERBOSE: print 'Producing an event record for the event titled "%s" at "%s":' % (event['displayName'], venue['displayName'])
        fsq_venue = get_foursquare_venue_normalization(venue, fsq=fsq)
        checkins = fsq_venue['hereNow']['count']
        if VERBOSE: print '\t\tFoursquare venue "%s" found' % fsq_venue['name']
        if VERBOSE: print '\t\tSongkick venue capacity %s' % str(venue_capacity)

        event_record = dict(
            title=event_name,
            # TODO: time,
            venue_name=venue_name,
            venue_capacity=venue_capacity,
            performers_names=map(lambda a: a['name'], performers),
            performers_playcounts=map(lambda a: a['playcount'], performers),
        )
        print event_record
        ret_events.append(event_record)
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
