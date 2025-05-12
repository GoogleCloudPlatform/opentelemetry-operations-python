# Copyright 2025 Google LLC
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

from typing import Iterable

from langchain_core.messages.base import BaseMessage
from rich.console import Console
from rich.markdown import Markdown

console = Console()


def render_messages(messages: Iterable[BaseMessage]) -> None:
    for message in messages:
        _render_message(message)
    print_markdown("---")


def _render_message(message: BaseMessage) -> None:
    # Filter out tool calls
    if message.type not in ("human", "ai"):
        return

    content = (
        message.content
        if isinstance(message.content, str)
        else message.content[-1]["text"]
    ).strip()

    # Response was probably blocked by a harm category, go check the trace for details
    if message.response_metadata.get("is_blocked", False):
        console.print("❌ Response blocked, try again")

    if not content:
        return

    if message.type == "human":
        print_markdown(f"👤 User:\n{content}")
    else:
        print_markdown(f"🤖 Agent:\n{content}")


def print_markdown(markdown: str) -> None:
    console.print(Markdown(markdown))


def ask_prompt() -> str:
    return console.input("[bold magenta]Talk to the SQL agent >> [/]")
