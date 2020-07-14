#!/bin/bash
[[ -z "$1" ]] && { echo "Enter a commit message. e.g. bash everything.sh 'commit_msg'" ; exit 1; }
set -e

tox -e lint

tox -e test

tox -e docs

git add .
git reset HEAD everything.sh
git reset HEAD opentelemetry-api/src/opentelemetry/__init__.pyi
git reset HEAD tox.ini
git reset HEAD ext/opentelemetry-ext-requests/src/opentelemetry/ext/requests/__init__.py
git commit -m "$1"
git push
