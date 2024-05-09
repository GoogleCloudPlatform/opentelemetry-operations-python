FROM python:3.12
WORKDIR /usr/src/app
COPY . .
RUN python -m venv /venv && \
    /venv/bin/pip install -r requirements.txt
CMD bash -c "source /venv/bin/activate && flask run --host 0.0.0.0 --port 8080 2>&1 | tee /var/log/app.log"