import datetime

import flask
from flask.ext.couchdb import *

from eventwarning import couchdb_manager

class DangerEntry(Document):
    doc_type = 'danger_entry'
    title = TextField()
    time = DateTimeField()
    venue = TextField()
    performers = ListField(TextField())

    fsq_venue = DictField()
    lfm_performers = ListField(DictField())
    eventful_performers = ListField(DictField())
    eventful_event = DictField()

    updated = DateTimeField(default=datetime.datetime.now())

couchdb_manager.add_document(DangerEntry)

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
