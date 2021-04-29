import os

if "PORT" not in os.environ:
    raise Exception("Must supply environment variable PORT")

bind = "0.0.0.0:{}".format(os.environ["PORT"])

# Needed to prevent forking for OTel
workers = 1

wsgi_app = "server:app"

# log requests to stdout
accesslog = "-"
