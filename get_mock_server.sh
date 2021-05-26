#!/bin/bash
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
