# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Literal

from cloudevents.http.event import CloudEvent
import functions_framework
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.subscriber.message import Message
from google.rpc import code_pb2

from . import scenarios, types
from .constants import (
    PROJECT_ID,
    PUSH_PORT,
    REQUEST_SUBSCRIPTION_NAME,
    RESPONSE_TOPIC_NAME,
    SCENARIO,
    STATUS_CODE,
    TEST_ID,
)

logger = logging.getLogger(__name__)


class _Responder:
    """Wraps pubsub publisher client back to the test server"""

    def __init__(self) -> None:
        self._publisher = pubsub_v1.PublisherClient(
            # disable buffering
            batch_settings=pubsub_v1.types.BatchSettings(max_messages=1)
        )
        self._response_topic = self._publisher.topic_path(
            PROJECT_ID, RESPONSE_TOPIC_NAME
        )

    def respond(
        self,
        test_id: str,
        res: scenarios.Response,
    ) -> None:
        """Respond to the test runner that we finished executing the scenario"""
        data = res.data
        attributes = {
            **res.headers,
            TEST_ID: test_id,
            STATUS_CODE: str(res.status_code),
        }
        logger.info(f"publishing {data=} and {attributes=}")

        self._publisher.publish(
            self._response_topic,
            data,
            **attributes,
        )


def handle_message(
    message: types.PubsubMessage, responder: _Responder
) -> Literal["ack", "nack"]:
    """Execute a scenario based on the incoming message from the test runner.
    Return whether to ack or nack the message"""
    if TEST_ID not in message.attributes:
        # don't even know how to write back to the publisher that the
        # message is invalid, so nack()
        return "nack"
    test_id: str = message.attributes[TEST_ID]

    if SCENARIO not in message.attributes:
        responder.respond(
            test_id,
            scenarios.Response(
                status_code=code_pb2.INVALID_ARGUMENT,
                data=f'Expected attribute "{SCENARIO}" is missing'.encode(),
            ),
        )
        return "ack"

    scenario = message.attributes[SCENARIO]
    handler = scenarios.SCENARIO_TO_HANDLER.get(
        scenario, scenarios.not_implemented_handler
    )

    try:
        res = handler(
            scenarios.Request(
                test_id=test_id,
                headers=dict(message.attributes),
                data=message.data,
            )
        )
    except Exception as e:
        logger.exception("exception trying to handle request")
        res = scenarios.Response(
            status_code=code_pb2.INTERNAL, data=str(e).encode()
        )
    finally:
        responder.respond(test_id, res)
        return "ack"


def pubsub_pull() -> None:
    """Pull incoming pub/sub push messages on REQUEST_SUBSCRIPTION_NAME"""
    responder = _Responder()
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        PROJECT_ID,
        REQUEST_SUBSCRIPTION_NAME,
    )

    def pubsub_callback(message: Message) -> None:
        ack_or_nack = handle_message(
            types.PubsubMessage(
                attributes=message.attributes, data=message.data
            ),
            responder,
        )
        if ack_or_nack == "ack":
            message.ack()
        else:
            message.nack()

    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=pubsub_callback
    )

    logger.info(
        "Listening on subscription {} for pub/sub messages".format(
            REQUEST_SUBSCRIPTION_NAME
        )
    )
    with subscriber:
        streaming_pull_future.result()


def pubsub_push() -> None:
    """Start a web server listening for incoming pub/sub push message"""
    from flask import Flask, Response, request
    from waitress import serve

    app = Flask(__name__)
    responder = _Responder()

    @app.route("/", methods=["POST"])
    def index() -> Response:
        if not request.is_json:
            return Response("Expected a JSON payload", status=400)
        payload = types.PubsubPushPayload(**request.json)

        ack_or_nack = handle_message(
            payload.message.to_pubsub_message(), responder
        )
        if ack_or_nack == "ack":
            return Response(status=200)
        else:
            return Response(status=400)

    serve(app, port=PUSH_PORT)


@functions_framework.cloud_event
def cloud_functions_handler(cloud_event: CloudEvent) -> None:
    """Handles pub/sub push message on Cloud Functions"""
    # cloud_event.data is of type MessagePublishedData, i.e. it contains the pub/sub message
    # https://github.com/googleapis/google-cloudevents/blob/v2.1.6/proto/google/events/cloud/pubsub/v1/data.proto#L26
    payload = types.PubsubPushPayload(**cloud_event.data)

    ack_or_nack = handle_message(
        payload.message.to_pubsub_message(), _Responder()
    )
    if ack_or_nack == "nack":
        raise Exception("Nacking message")
