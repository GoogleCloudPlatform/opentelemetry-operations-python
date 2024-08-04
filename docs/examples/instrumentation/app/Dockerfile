FROM python:3.12
WORKDIR /usr/src/app
COPY . .
RUN python -m venv /venv && \
    /venv/bin/pip install .
CMD bash -c "source /venv/bin/activate && opentelemetry-instrument flask run --host 0.0.0.0 2>&1 | tee /var/log/app.log"
