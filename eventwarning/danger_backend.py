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

### Event handling helper functions ###

def songkick_events_for_day(day, zip):
    """
    Given a date object `day` and a `zip`, finds and returns events from
    Songkick.

    The returned events are in a more or less API-agnostic format, so they
    should be suitably normalized so as to be mergeable with, say, Eventful
    events if so desired.

    Parameters
    ==========

        `day`
            The date for the search, a Python datetime or date object.

        `zip`
            The zip code to search in, a string.

    Returns
    =======

        A list of 3-tuples of the following format:

        ``(
            event,
            venue,
            performers
        )``

        where:

        `event`
            The DangerEntry-formatted dictionary of event-only details as
            returned by `songkick_event_to_danger_event`.

        `venue`
            The DangerEntry-formatted dictionary of the event's venue, as
            returned by `songkick_event_to_venue_dict`.

        `performers`
            A list of the event's performers, as normalized to Last.fm and
            returned by `get_sk_performer_list` in dictionary format.

    """
    sk = songkick.SongkickAPI(SK_KEY)
    loc_db = models.ZipCode.load('/locations/zip/%s' % zip)
    loc = 'geo:%s,%s' % (loc_db.lat, loc_db.lon)
    date = day.strftime('%Y-%m-%d')
    all_events = sk.event_search(location=loc, min_date=date, max_date=date)
    zip_events = []
    for event in all_events:
        venue_sk = sk.venue_details(event['venue']['id'])
        if venue_sk['zip'] == zip:
            zip_events.append((
                songkick_event_to_danger_event(event),
                songkick_event_to_venue_dict(event, venue_sk=venue_sk, sk=sk),
                get_sk_performer_list(event)
            ))
    return zip_events

def songkick_event_to_danger_event(event_sk):
    """
    Given a raw songkick event `event_sk` returns a more `models.DangerEntry`
    compatible dictionary.

    No venue or performer data is encoded.

    Parameters
    ==========

    `event_sk`
        A raw Songkick event

    Returns
    =======

    A dictionary representing the event with the following fields:

    `title`
        The display name of the event

    `url_sk`
        The URL for the Songkick event page for the event

    `time`
        A Datetime object representing the start time of the event. Currently
        non-working.
    """

    return dict(
        title = event_sk['displayName'],
        url_sk = event_sk['uri'],
        # time=datetime.datetime.strptime(
        #    event_sk['start']['datetime'],
        #    '%Y-%m-%dT%H:%M:%S%z' # ?????
        #)
    )

def songkick_event_to_venue_dict(event_sk, venue_sk=None, sk=None):
    """
    Given a raw songkick event `event_sk` returns a more `models.DangerEntry`
    compatible venue dictionary.

    Parameters
    ==========

    `event_sk`
        A raw Songkick event

    `venue_sk`
        A raw Songkick venue detail object, or None to look it up.

    `sk`
        A connected Songkick API object, or None to create a new one.

    Returns
    =======

    A dictionary representing the event's venue with the following fields:

    `name`
        The display name of the venue (via Songkick).

    `capacity`
        The venue's capacity as reported by Songkick, or `None` if unknown.

    `url_sk`
        The URL for the Songkick page for the venue.

    `id_fsq`
        Our guess at the Foursquare ID of the venue.
    """

    if not sk:
        sk = songkick.SongkickAPI(SK_KEY)

    if not venue_sk:
        venue_sk = sk.venue_details(event_sk['venue']['id'])

    venue_fsq = get_foursquare_venue_normalization(venue_sk)

    return dict(
        name = venue_sk['displayName'],
        capacity = venue_sk['capacity'],
        url_sk = venue_sk['uri'],
        id_fsq = venue_fsq['id'],
    )

### Performer handling ###

def get_sk_performer_list(event, lfm=None):
    """
    Given a raw Songkick `event` and optional last.fm API `lfm` return
    a list of the event's performers.

    For now, we are assuming that each performer['artist']['identifier'] list
    has length 1, which is an assertion. I'm unsure of the Songkick contract
    regarding identifier lists, so this may or may not be a bad assumption to
    make.

    If a last.fm performer lookup fails, rather than trying to guess at what
    to call the performer, we just skip it. In the future, some guess might be
    valuable.

    Parameters
    ==========

    `event`
        The raw event as returned from the Songkick API

    `lfm`
        An initialized pylast LastFMNetwork object, or None to use a new one.

    Returns
    =======

    A list of dictionaries representing performers as returned by
    `get_lfm_performer`. The dictionary has the following entries:

    `name`
        The artist's last.fm display name
    `playcount`
        The artist's playcount on last.fm at time of retrieval
    `mbid`
        The artist's MusicBrainz ID
    `url`
        The artist's URL on last.fm
    """
    if not lfm:
        lfm = pylast.LastFMNetwork(api_key=LFM_KEY, api_secret=LFM_SEC)
    sk_performers = []
    performers = event['performance']
    for performer in performers:
        mbid = None
        if performer['artist']['identifier']:
            # TODO: handle longer than 1? (see note in docstring)
            assert len(performer['artist']['identifier'])==1
            mbid = performer['artist']['identifier'][0].get('mbid', None)

        try:
            lfm_performer = get_lfm_performer(
                mbid=mbid,
                name=performer['artist']['displayName'],
                lfm=lfm
            )
            sk_performers.append(lfm_performer)
        except pylast.WSError:
            # Failed to look up the performer. TODO: guess at what to call it?
            # See note in docstring.
            pass
    return sk_performers

def get_lfm_performer(mbid=None, name=None, lfm=None):
    """
    Given a `mbid` and/or artist `name`, return last.fm artist details.

    First we try to look up by MBID only. If that fails, or if no MBID was
    provided, we try an artist name lookup. If none of that yielded an artist,
    we return an empty dictionary.

    A `pylast.WSError` is raised if the lookup failed.

    TODO: should we return None?

    Parameters
    ==========

    `mbid`
        The artist's MusicBrainz ID

    `name`
        The artist's name

    `lfm`
        An initialized pylast LastFMNetwork object, or None to use a new one.

    Returns
    =======

    If the artist is found, return a dictionary representing the artist as
    looked up on last.fm. If the artist is not found, returns an empty dict.
    A successful lookup dictionary contains the following entries:

    `name`
        The artist's last.fm display name
    `playcount`
        The artist's playcount on last.fm at time of retrieval
    `mbid`
        The artist's MusicBrainz ID
    `url`
        The artist's URL on last.fm
    """

    # Create a new pylast connection if necessary:
    if not lfm:
        lfm = pylast.LastFMNetwork(api_key=LFM_KEY, api_secret=LFM_SEC)

    # We need *some* information to search:
    assert mbid or name
    artist = None

    # Try using the MBID if we have it.
    # TODO: deal with the WSError here?
    if mbid:
        artist = lfm.get_artist_by_mbid(mbid)

    # If MBID lookup failed or MBID wasn't provided, do it by name:
    if name and not mbid or not artist:
        artist = lfm.get_artist(name)

    # Return the dict
    artist_dict = {}
    if artist:
        artist_dict.update(
            name=artist.name,
            playcount=artist.get_playcount(),
            mbid=artist.get_mbid(),
            url=artist.get_url()
        )
    return artist_dict


def get_eventful_performer_list(event, lfm=None):
    """
    Given a raw Eventful `event` and optional last.fm API `lfm` return
    a list of the event's performers.

    Currently not implemented.

    Parameters
    ==========

    `event`
        The raw event as returned from the Eventful API

    `lfm`
        An initialized pylast LastFMNetwork object, or None to use a new one.

    Returns
    =======

    A list of dictionaries representing performers as returned by
    `get_lfm_performer`. The dictionary has the following entries:

    `name`
        The artist's last.fm display name
    `playcount`
        The artist's playcount on last.fm at time of retrieval
    `mbid`
        The artist's MusicBrainz ID
    `url`
        The artist's URL on last.fm
    """
    raise NotImplementedError()

def get_total_lfm_plays_for_event(event):
    """
    Given an `event` in our `models.DangerEntry` dictionary format, return its
    performers' total playcounts.

    Parameters
    ==========

    `event`
        A dictionary, as in the `models.DangerEntry` format

    Returns
    =======

    The sum of the event's last.fm performers' play counts.

    """
    return reduce(
        operator.add,
        (performer['playcount'] for performer in event['performers']),
        0
    )

### Venue handling ###

def get_foursquare_venue_normalization(sk_venue, fsq=None):
    """
    Given a songkick venue `sk_venue`, return a guess at a Foursquare location.

    Parameters
    ==========

    `sk_venue`
        The raw Songkick venue details object representing the venue.

    `fsq`
        An initialized foursquare API connection object, or None to create
        a new one.

    Returns
    =======

    A foursquare object representing the venue.
    """
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

### The danger/attendance estimate ###

def get_attendance_estimate_for_event(event):
    """
    Given a nearly complete `models.DangerEntry` compatible event dict,
    return its estimated attendance.

    Parameters
    ==========

    `event`
        A `models.DangerEntry` formatted event dictionary. It must have
        a ``venue`` key, whose value must have a ``capacity`` key.
        `get_total_lfm_plays_for_event` also requires its ``performers``
        entry to be iterable and, if any exist, be dictionaries with
        the ``playcount`` key.

    Returns
    =======

    A really bad estimate of the attendance for this event, in the form of
    an `int`.
    """
    # If we don't know the capacity, we'll assume it's bar sized (100ish).
    # Otherwise we'll need to fix the venue on songkick.
    capacity = event['venue']['capacity'] or 100
    lfm_plays = get_total_lfm_plays_for_event(event)
    attendance_possible = lfm_plays / 500.0
    # TODO?: This is pretty darn simplistic.
    attendance = min(capacity, attendance_possible)
    return attendance

def get_events_for_day(day):
    """
    Returns a list of `models.DangerEntry.events` formatted events for
    the given date `day`.

    It looks them up using Songkick and may in the future support merging
    Songkick results with Eventful results. Songkick has issues looking into
    the past, so only future events should be considered reliable.

    Parameters
    ==========

    `day`
        A `datetime.date` object representing the day to check.

    Returns
    =======

    A list of dictionaries in the format of the `models.DangerEntry.events`
    field.
    """

    ret_events = []

    # Grab the day's events in the desired zip code:
    songkick_event_venues = songkick_events_for_day(day, '74103')

    # TODO: grab eventful's events for the same area/day
    # TODO: merge them

    event_venues = songkick_event_venues

    # Now, let's check out each event individually:
    for event, venue, performers in event_venues:
        if VERBOSE: print 'Producing an event record for the event titled ' \
                          '"%s" at "%s":' % (event['title'], venue['name'])

        # Add the venues and performers to the event:
        event.update(
            venue=venue,
            performers=performers,
        )

        # Compute and incorporate attendance estimates and total plays:
        event.update(
            attendance_estimate=get_attendance_estimate_for_event(event),
            total_plays_lfm=get_total_lfm_plays_for_event(event),
        )

        ret_events.append(event)
    return ret_events
