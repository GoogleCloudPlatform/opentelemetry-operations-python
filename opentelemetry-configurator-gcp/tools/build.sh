#!/bin/bash

SCRIPT_DIR=$(cd $(dirname ${BASH_SOURCE:-0}); pwd)
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
BUILD_DIR="${PROJECT_DIR}/.build"
BUILD_ENV="${BUILD_DIR}/.venv"

function main() {
    if [ ! -d "${BUILD_ENV}" ] ; then
      mkdir -p "${BUILD_ENV}"
    fi
    if [ ! -d "${BUILD_ENV}/bin" ] ; then
      python3 -m venv "${BUILD_ENV}"
    fi

    source "${BUILD_ENV}/bin/activate"
    pip install build
 
    cd "${PROJECT_DIR}"
    python3 -m build
}

main
