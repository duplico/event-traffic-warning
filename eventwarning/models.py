import datetime

import flask
from flask.ext.couchdb import *

from eventwarning import couchdb_manager
from eventwarning import danger_backend as danger

class DangerEntry(Document):
    """
    Represents one day's events at one location.
    """
    doc_type = 'danger_entry'
    location = TextField() # Zip code
    date = DateField()

    events = ListField(
        DictField(Mapping.build(
            title = TextField(),
            time = DateTimeField(),
            venue_name = TextField(),
            venue_fsq = DictField(),
            venue_songkick = DictField(),
            venue_capacity = IntegerField(),
            performers_names = ListField(TextField()),
            performers_lfm = ListField(DictField()),
            performers_eventful = ListField(DictField()), # TODO: don't use?
            event_eventful = DictField(),
            event_songkick = DictField(),
            attendance_estimate = IntegerField(),
        ))
    )
    updated = DateTimeField(default=datetime.datetime.now())

    def prioritized(self):
        out_events = dict(useful=[], useless=[])
        out_needs_info = []
        for event in self.events:
            if not event['performers_names']:
                out_events['useless'].append(event)
            else:
                out_events['useful'].append(event)
            if not event['venue_capacity']:
                out_needs_info.append(event) # TODO: refactor
        return out_events

    def total(self):
        attendance_total = 0
        for event in self.events:
            attendance_total += event.get('attendance_estimate', 0)
        return attendance_total

couchdb_manager.add_document(DangerEntry)

def get_or_create_danger_entry(day, zip):
    id = '/dangers/zip/%s/d/%s' % (zip, day.strftime('%Y-%m-%d'))
    danger_record = DangerEntry.load(id)
    if danger_record:
        return danger_record
    #    return danger_record

    events = []
    # TODO: refactor
    event_structs = danger.get_events_for_day(day)
    for event in event_structs:
        lfm_performers = []
        for performer in event.lfm_performers:
            lfm_performers.append(dict(
                name=str(performer.name),
                playcount=int(performer.get_playcount()),
                url=str(performer.get_url()),
            ))
        event_db = dict(
            title=event.title,
            time=datetime.datetime.strptime(event.time, '%Y-%m-%d %H:%M:%S'),
            venue_name=event.venue,
            venue_fsq=event.fsq_venue,
            venue_songkick=event.sk_venue,
            venue_capacity=event.venue_capacity,
            performers_names=event.performers,
            performers_lfm=lfm_performers,
            performers_eventful=event.eventful_performers,
            event_eventful=event.eventful_event,
            event_songkick={},
            attendance_estimate=event.get_attendance_estimate(),
        )
        events.append(event_db)
    danger_record = DangerEntry(
        location=zip,
        date=day,
        events=events,
    )
    danger_record.id = id
    danger_record.store()
    return danger_record

#
#class User(Document, UserMixin):
#    doc_type = 'user'
#    username = TextField()
#    pw_hash = TextField()
#    email_address = TextField()
#    admin = BooleanField(default=False)
#
#    shared_scenarios = ListField(DictField(Mapping.build(
#        dest_username=TextField(),
#        src_username=TextField(), # DENORMALIZATION IS AWESOME :)
#        ag_name=TextField())))
#
#    shared_with = ViewField('User', '''\
#    function (doc) {
#        if (doc.doc_type == 'user') {
#            doc.shared_scenarios.forEach(function (scenario) {
#                emit(scenario.dest_username, scenario);
#            });
#        };
#    }''', wrapper=Row)
#
#    def matches_password(self, raw_password):
#        return check_password_hash(self.pw_hash, raw_password)
#
#    def get_auth_token(self):
#        hasher = hashlib.sha256()
#        hasher.update(self.username)
#        hasher.update(self.pw_hash)
#        return unicode(hasher.hexdigest())
#
#    def available_scenarios(self):
#        explicit = [(row.value['src_username'], row.value['ag_name']) \
#                    for row in User.shared_with[self.username]]
#        implicit = [(row.value['src_username'], row.value['ag_name']) \
#                    for row in User.shared_with['*']]
#        return list(set(explicit + implicit))
#
#couchdb_manager.add_document(User)
#
#def load_user(username):
#    """ Returns None if not found. """
#    return User.load(username.lower()) or User.load(username)
#
#@login_manager.user_loader
#def loaduser(username):
#    """ Returns None if not found. """
#    return load_user(username)
