#!/bin/bash

SCRIPT_DIR=$(cd $(dirname ${BASH_SOURCE:-0}); pwd)
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
TESTS_DIR="${PROJECT_DIR}/tests"
TESTS_ENV="${PROJECT_DIR}/.test/.test-venv"

function main() {
    if [ ! -d "${TESTS_ENV}" ] ; then
      mkdir -p "${TESTS_ENV}"
    fi
    if [ ! -d "${TESTS_ENV}/bin" ] ; then
      python3 -m venv "${TESTS_ENV}"
    fi

    source "${TESTS_ENV}/bin/activate"
    pip install -r "${TESTS_DIR}/requirements.txt"
    python3 "$@"
}

main "$@"
