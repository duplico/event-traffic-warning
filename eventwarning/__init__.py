from flask import Flask
from flaskext.couchdb import CouchDBManager

app = Flask(__name__)

app.debug = True

# Config
#try:
#    from ag_web_settings import config as local_config
#    app.config.update(local_config)
#except ImportError:
#    print 'Failed to import local configuration.'

app.config.setdefault('COUCHDB_SERVER', 'http://localhost:5984/')
app.config.setdefault('COUCHDB_DATABASE', 'eventwarning')
app.config.setdefault('DISABLE_AUTO_SYNCING', True)

# Set up flask specific stuff:
couchdb_manager = CouchDBManager(auto_sync=False)

couchdb_manager.setup(app)
# do stuff (set up more app things, maybe make some objects)

couchdb_manager.sync(app)

import views
