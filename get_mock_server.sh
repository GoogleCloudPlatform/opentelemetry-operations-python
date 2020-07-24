#!/bin/bash

if ! [ -e $1/mock_server-x64-linux ]; then
  curl -L -o $1/mock_server-x64-linux https://github.com/googleinterns/cloud-operations-api-mock/raw/master/cmd/mock_server-x64-linux
  chmod +x $1/mock_server-x64-linux
fi

