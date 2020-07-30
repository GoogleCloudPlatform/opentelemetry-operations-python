#!/bin/bash

if ! [ -e $1/mock_server-x64-linux-v1-alpha ]; then
  curl -L -o $1/mock_server-x64-linux-v1-alpha https://github.com/googleinterns/cloud-operations-api-mock/releases/download/v1-alpha/mock_server-x64-linux-v1-alpha
  chmod +x $1/mock_server-x64-linux-v1-alpha
fi

