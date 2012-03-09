from datetime import datetime

from flask import request, make_response, render_template, url_for, flash
from flask import redirect
import flask

import danger_backend as danger
#danger.VERBOSE = False

from eventwarning import app
from eventwarning import models
from eventwarning import executor, running_futures

DEFAULT_ZIP = "74103"

# /
# /zip/<zip>/d/<date>
#
#

@app.route('/', methods=['GET',])
def landing():
    return redirect(url_for('danger_zip', zip='74103',
                            date=datetime.now().strftime('%Y-%m-%d')))

@app.route('/d/<date>/')
def default_zip_danger(date):
    return danger_zip(DEFAULT_ZIP, date)

@app.route('/zip/<zip>/d/<date>/', methods=['GET',])
def danger_zip(zip, date):

    day_obj = datetime.strptime(date, '%Y-%m-%d').date()

    id = '/dangers/zip/%s/d/%s' % (zip, day_obj.strftime('%Y-%m-%d'))
    danger_record = models.DangerEntry.load(id)

    if not danger_record:
        if id in running_futures:
            if running_futures[id].done():
                danger_record = running_futures[id].result()
            else:
                pass # In progress
        else:
            running_futures[id] = executor.submit(
                models.get_or_create_danger_entry,
                day_obj,
                zip,
                db=flask.g.couch
            )
            # In progress

    if not danger_record:
        return make_response('In progress\n', 202)
        return render_template(
            'events.html',
            zip=zip,
            day=day_obj,
            events=None,
        )

    tweet = danger_record.get_tweet()

    events_prioritized = danger_record.prioritized()
    region_capacity = danger.get_zip_capacity('74103')
    percent = int((100.0 * danger_record.total() / region_capacity))
    percent_str = '%d%%' % percent

    return render_template(
        'events.html',
        zip=zip,
        events=events_prioritized['useful'],
        other_events=events_prioritized['useless'],
        total=danger_record.total(),
        day=day_obj,
        region_capacity=region_capacity,
        percent_str=percent_str,
        percent=percent,
        tweet=tweet,
    )

@app.route('/q/z/<zip>/d/<date>/', methods=['GET',])
def query_danger_status(zip, date):
    day_obj = datetime.strptime(date, '%Y-%m-%d').date()

    events = models.get_or_create_danger_entry(day_obj, zip)
    events_prioritized = events.prioritized()

    region_capacity = danger.get_zip_capacity('74103')
    percent = int((100.0 * events.total() / region_capacity))
    percent_str = '%d%%' % percent

    print events.get_tweet()

    return render_template(
        'events.html',
        zip=zip,
        events=events_prioritized['useful'],
        other_events=events_prioritized['useless'],
        total=events.total(),
        day=day_obj,
        region_capacity=region_capacity,
        percent_str=percent_str,
        percent=percent
    )

@app.route('/locations/index_zips/', methods=['POST',])
def index_zips():
    # curl -X POST http://localhost:5000/locations/index_zips/?key=ADMIN_SECRET
    if request.args.get('key', None) == app.config.get('ADMIN_SECRET'):
        if 'index_zips' in running_futures:
            print 'in'
            if running_futures['index_zips'].done():
                return make_response('/locations/\n', 200)
            else:
                return make_response('In progress\n', 202)
        else:
            task = executor.submit(models.store_all_zips,
                                   app.config.get('ZIP_DB'),
                                   db=flask.g.couch)
            running_futures['index_zips'] = task
        return make_response('Job started\n', 202)
    else:
        return make_response('INVALID SECRET\n', 403)

@app.route('/p<shortcut>', methods=['GET',])
def shortcut_entry(shortcut):
    pass
