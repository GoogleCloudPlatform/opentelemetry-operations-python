#! /bin/bash

set -o pipefail

SCRIPT_DIR=$(cd $(dirname ${BASH_SOURCE:-0}); pwd)
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
TESTS_DIR="${PROJECT_DIR}/tests"
TEST_ENV="${PROJECT_DIR}/.test/.venv-auto"

function main() {
    if [ ! -d "${TEST_ENV}" ] ; then
      mkdir -p "${TEST_ENV}" || exit 1
    fi
    if [ ! -d "${TEST_ENV}/bin" ] ; then
      python3 -m venv "${TEST_ENV}" || exit 1
    fi

    source "${TEST_ENV}/bin/activate" || exit 1
    pip install -r "${TESTS_DIR}/requirements.txt" || exit 1
 
    cd "${PROJECT_DIR}" || exit 1
    make install || exit 1
    pip install opentelemetry-instrumentation || exit 1
    pip install opentelemetry-distro || exit 1

    opentelemetry-instrument \
      --configurator=gcp \
      python \
      "${TESTS_DIR}/run_with_autoinstrumentation.py" || exit $?
}

main
