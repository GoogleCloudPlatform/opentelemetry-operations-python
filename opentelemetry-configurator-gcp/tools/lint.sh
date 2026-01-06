#!/bin/bash

set -o pipefail

SCRIPT_DIR=$(cd $(dirname ${BASH_SOURCE:-0}); pwd)
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
BUILD_DIR="${PROJECT_DIR}/.build"
LINT_ENV="${BUILD_DIR}/.lint-venv"
LINT_REQUIREMENTS="${PROJECT_DIR}/tests/requirements.txt"

function main() {
    if [ ! -d "${LINT_ENV}" ] ; then
      mkdir -p "${LINT_ENV}" || exit 1
    fi
    if [ ! -d "${LINT_ENV}/bin" ] ; then
      python3 -m venv "${LINT_ENV}" || exit 1
    fi

    source "${LINT_ENV}/bin/activate" || exit 1
    pip install -r ${LINT_REQUIREMENTS} || exit 1
    pip install pylint || exit 1
 
    cd "${PROJECT_DIR}" || exit 1
    pylint src
}

main
