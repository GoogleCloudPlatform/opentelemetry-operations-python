# Copyright 2021 Google
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

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.subscriber.message import Message
from google.rpc import code_pb2

from . import scenarios
from .constants import (
    PROJECT_ID,
    REQUEST_SUBSCRIPTION_NAME,
    RESPONSE_TOPIC_NAME,
    SCENARIO,
    STATUS_CODE,
    TEST_ID,
)

logger = logging.getLogger(__name__)


def pubsub_pull() -> None:
    publisher = pubsub_v1.PublisherClient(
        # disable buffering
        batch_settings=pubsub_v1.types.BatchSettings(max_messages=1)
    )
    response_topic = publisher.topic_path(PROJECT_ID, RESPONSE_TOPIC_NAME)

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        PROJECT_ID, REQUEST_SUBSCRIPTION_NAME,
    )

    def respond(test_id: str, res: scenarios.Response) -> None:
        """Respond to the test runner that we finished executing the scenario"""
        data = res.data
        attributes = {TEST_ID: test_id, STATUS_CODE: str(res.status_code)}
        logger.info(f"publishing {data=} and {attributes=}")
        publisher.publish(
            response_topic, data, **attributes,
        )

    def pubsub_callback(message: Message) -> None:
        """Execute a scenario based on the incoming message from the test runner"""
        if TEST_ID not in message.attributes:
            # don't even know how to write back to the publisher that the
            # message is invalid, so nack()
            message.nack()
            return
        test_id: str = message.attributes[TEST_ID]

        if SCENARIO not in message.attributes:
            respond(
                test_id,
                scenarios.Response(
                    status_code=code_pb2.INVALID_ARGUMENT,
                    data=f'Expected attribute "{SCENARIO}" is missing'.encode(),
                ),
            )
            message.ack()
            return

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
            respond(test_id, res)
            message.ack()

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
