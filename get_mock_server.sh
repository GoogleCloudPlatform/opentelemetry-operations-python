#!/bin/bash

# Use this envvar when testing a local mock_server binary
if [ "$SKIP_GET_MOCK_SERVER" == "true" ]; then
  exit
fi

VERSION=v2-alpha
BINARY=mock_server-x64-linux-$VERSION
if ! [ -e $1/$BINARY ]; then
  curl -L -o $1/$BINARY https://github.com/googleinterns/cloud-operations-api-mock/releases/download/$VERSION/$BINARY
  chmod +x $1/$BINARY
fi

ln -sf $1/$BINARY $1/mock_server
