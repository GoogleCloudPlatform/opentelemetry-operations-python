FROM python:3.12
WORKDIR /usr/src/app
COPY . .
RUN python -m venv /venv && \
    /venv/bin/pip install -r requirements.txt
# TODO: Make this a more realistic productionized application using Gunicorn as a SWGI server.
# See https://flask.palletsprojects.com/en/3.0.x/deploying/ 
CMD . /venv/bin/activate && flask run --host 0.0.0.0 --port 8080 2>&1 | tee /var/log/app.log