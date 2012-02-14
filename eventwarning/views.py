from datetime import datetime

from flask import request, make_response, render_template, url_for, flash
from flask import redirect
import flask

import danger_backend as danger
#danger.VERBOSE = False

from eventwarning import app

# /
# /zip/<zip>/<date>
#
#

@app.route('/', methods=['GET',])
def landing():
    pass

@app.route('/zip/<zip>/d/<date>/', methods=['GET',])
def danger_zip(zip, date):
    day_obj = datetime.strptime(date, '%Y-%m-%d').date()

    events = danger.prioritized_events_for_day(day_obj)
    total = danger.attendance_for_events(events['useful'])

    return render_template('events.html', zip=zip, events=events['useful'],
                           other_events=events['useless'], total=total)

