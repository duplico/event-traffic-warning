import datetime
import re

import flask
from flask.ext.couchdb import *
from unidecode import unidecode

from eventwarning import couchdb_manager
import danger_backend as danger

class ZipCode(Document):
    """
    Geocodes a zip code.
    """
    doc_type = 'zip'
    zip = TextField() # Zip code
    lat = TextField()
    lon = TextField()
    city = TextField()
    state = TextField()
    capacity = IntegerField()
    capacity_updated = DateTimeField()

couchdb_manager.add_document(ZipCode)

def store_all_zips(path_to_csv, db=None):
    """
    Build a stored zip code database. This must be done before running the app.

    CSV format:
    "zipcode";"state";"fips_regions";"city";"latitude";"longitude"
    """
    num_re = re.compile('[0-9]+')
    for line in open(path_to_csv):
        components = line.split(';')
        # Remove quotes:
        components = map(lambda a: unidecode(a.strip()[1:-1]), components)
        zip = components[0]
        # Heading/non number zip:
        if not num_re.match(zip):
            continue
        id = '/locations/zip/%s' % zip
        if ZipCode.load(id, db=db):
            continue
        state, regions, city, lat, long = components[1:]
        zc_doc = ZipCode(zip=zip, lat=lat, lon=long, city=city, state=state)
        zc_doc.id = id
        zc_doc.store(db=db)


#(
#            name=artist.name,
#            playcount=artist.get_playcount(),
#            mbid=artist.get_mbid(),
#            url=artist.get_url()
#        )

class DangerEntry(Document):
    """
    Represents one day's events at one location.
    """
    doc_type = 'danger_entry'
    location = TextField() # Zip code
    date = DateField()

    events = ListField(
        DictField(Mapping.build(
            # Event-specific data (songkick):
            title = TextField(),
            url_sk = TextField(),
            time = DateTimeField(),
            # Venue data (foursquare/songkick):
            venue = DictField(Mapping.build(
                name = TextField(),
                capacity = IntegerField(),
                url_sk = TextField(),
                id_fsq = TextField(),
            )),
            # Performer data (last.fm):
            performers = ListField(DictField(Mapping.build(
                name = TextField(),
                playcount = IntegerField(),
                mbid = TextField(),
                url_lfm = TextField(),
            ))),
            total_plays_lfm = IntegerField(),
            # Danger data (eventwarning):
            attendance_estimate = IntegerField(),
        ))
    )
    updated = DateTimeField(default=datetime.datetime.now())

    def prioritized(self):
        out_events = dict(useful=[], useless=[])
        out_needs_info = []
        for event in self.events:
            if not event['performers']:
                out_events['useless'].append(event)
            else:
                out_events['useful'].append(event)
            if not event['venue'] or not event['venue']['capacity']:
                out_needs_info.append(event) # TODO: refactor
        return out_events

    def total(self):
        attendance_total = 0
        for event in self.events:
            attendance_total += event.get('attendance_estimate', 0)
        return attendance_total

    @property
    def danger(self):
        region_capacity = danger.get_zip_capacity(self.location)
        percent = int((100.0 * self.total() / region_capacity))
        return percent

    def get_tweet(self):
        venues = [
            event['venue']['name'] for event in sorted(
                self.events,
                key=lambda e: e['venue']['capacity']
        )]
        venue_count = len(venues)
        venue_list_string = ', '.join(venues)
        url = 'evtl.in/pXXXXX'
        return '%d%% danger. %d events at: %s - %s' % (
            self.danger,
            venue_count,
            venue_list_string,
            url
        )

couchdb_manager.add_document(DangerEntry)

def get_or_create_danger_entry(day, zip, db=None):
    # TODO: base this off of the new dictionary format returned
    #   in ~danger_backend.py:164.

    id = '/dangers/zip/%s/d/%s' % (zip, day.strftime('%Y-%m-%d'))
    print 'pre-load'
    danger_record = DangerEntry.load(id, db=db)
    print 'post-load'
    if danger_record:
        return danger_record

    events = []
    print 'pre-get'
    event_structs = danger.get_events_for_day(day, db=db)
    print 'post-get'
    danger_record = DangerEntry(
        location=zip,
        date=day,
        events=event_structs,
    )
    danger_record.id = id
    print 'pre-store'
    danger_record.store(db=db)
    return danger_record
