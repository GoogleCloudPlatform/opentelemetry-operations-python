import flask
import random
import requests
import time

app = flask.Flask(__name__, static_folder=None)

@app.route('/multi')
def multi():
    for _ in range(random.randint(3, 7)):
        requests.get(flask.url_for('single', _external=True))
    return 'ok'

@app.route('/single')
def single():
    time.sleep(random.uniform(0.1, 0.3))
    return ''
