from concurrent import futures

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

app.config.setdefault('MAX_WORKERS', 5)
app.config.setdefault('COUCHDB_SERVER', 'http://localhost:5984/')
app.config.setdefault('COUCHDB_DATABASE', 'eventwarning')
app.config.setdefault('DISABLE_AUTO_SYNCING', True)
app.config.setdefault('ADMIN_SECRET', 'boobies123')
app.config.setdefault('ZIP_DB', 'eventwarning/zipcodes.csv')

executor = futures.ThreadPoolExecutor(max_workers=app.config['MAX_WORKERS'])
running_futures = dict()

# Set up flask specific stuff:
couchdb_manager = CouchDBManager(auto_sync=False)

couchdb_manager.setup(app)
# do stuff (set up more app things, maybe make some objects)
app.secret_key='ju=l8}C@+.D@ncYtU+mKw*}utALB1<'
couchdb_manager.sync(app)

import views
