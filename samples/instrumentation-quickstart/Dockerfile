FROM python:3.12
WORKDIR /usr/src/app
COPY . .
RUN python -m venv /venv && \
    /venv/bin/pip install -r requirements.txt
CMD . /venv/bin/activate && gunicorn -b 0.0.0.0:8080 -w 4 'app:app'  2>&1 | tee /var/log/app.log