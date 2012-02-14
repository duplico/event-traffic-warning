import datetime

import flask
from flask.ext.couchdb import *

from eventwarning import couchdb_manager

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
            time = DateTimeField,
            venue_name = TextField(),
            venue_fsq = DictField(),
            venue_songkick = DictField(),
            venue_capacity = IntegerField(),
            performers_names = ListField(TextField()),
            performers_lfm = ListField(DictField()),
            performers_eventful = ListField(DictField()), # TODO: don't use?
            event_eventful = DictField(),
            event_songkick = DictField()
        ))
    )
    updated = DateTimeField(default=datetime.datetime.now())

couchdb_manager.add_document(DangerEntry)
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
