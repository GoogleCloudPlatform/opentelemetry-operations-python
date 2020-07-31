#!/bin/bash
VERSION=v1-alpha
if ! [ -e $1/mock_server-x64-linux-$VERSION ]; then
  curl -L -o $1/mock_server-x64-linux-$VERSION https://github.com/googleinterns/cloud-operations-api-mock/releases/download/$VERSION/mock_server-x64-linux-$VERSION
  chmod +x $1/mock_server-x64-linux-$VERSION
fi

ln -sf $1/mock_server-x64-linux-$VERSION $1/mock_server

