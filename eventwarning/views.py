from datetime import datetime

from flask import request, make_response, render_template, url_for, flash
from flask import redirect
import flask

import danger_backend as danger
#danger.VERBOSE = False

from eventwarning import app
from eventwarning import models

# /
# /zip/<zip>/d/<date>
#
#

@app.route('/', methods=['GET',])
def landing():
    pass

@app.route('/zip/<zip>/d/<date>/', methods=['GET',])
def danger_zip(zip, date):
    day_obj = datetime.strptime(date, '%Y-%m-%d').date()

    events = models.get_or_create_danger_entry(day_obj, zip)
    events_prioritized = events.prioritized()

    return render_template(
        'events.html',
        zip=zip,
        events=events_prioritized['useful'],
        other_events=events_prioritized['useless'],
        total=events.total(),
        day=day_obj,
    )

