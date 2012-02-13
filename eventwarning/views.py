from flask import request, make_response, render_template, url_for, flash
from flask import redirect
import flask

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
    #return 'danger for %s on %s' % (zip, date)
    return render_template('base.html')
    return render_template('scenario.html', name=name, ag=ag,
                           nm=nm, xp=xp, owner=owner_username)

