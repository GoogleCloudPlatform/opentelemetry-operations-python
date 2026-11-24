#!/bin/bash

set -o pipefail

SCRIPT_DIR=$(cd $(dirname ${BASH_SOURCE:-0}); pwd)
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
TESTS_DIR="${PROJECT_DIR}/tests"
TEST_ENV="${PROJECT_DIR}/.test/.venv"

function main() {
    if [ ! -d "${TEST_ENV}" ] ; then
      mkdir -p "${TEST_ENV}" || exit 1
    fi
    if [ ! -d "${TEST_ENV}/bin" ] ; then
      python3 -m venv "${TEST_ENV}" || exit 1
    fi

    source "${TEST_ENV}/bin/activate" || exit 1
    pip install pytest || exit $?
    pip install -r "${TESTS_DIR}/requirements.txt" || exit $?
 
    cd "${PROJECT_DIR}" || exit 1
    export PYTHONPATH="${PYTHONPATH}:${PROJECT_DIR}/src"
    pytest "${TESTS_DIR}" -o log_cli_level=debug $@ || exit $?
}

main
