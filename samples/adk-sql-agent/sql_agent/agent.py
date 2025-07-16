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

from google.adk.agents import Agent
from .tools import run_sql_tool, create_database_tool

import sqlite3

from opentelemetry import trace

# from utils import ask_prompt, console, print_markdown, render_messages


SYSTEM_PROMPT = f"""\
You are a helpful AI assistant with a mastery of database design and querying. You have access
to an ephemeral sqlite3 database that you can query and modify through some tools. Help answer
questions and perform actions. Follow these rules:

- Make sure you always use sql_db_query_checker to validate SQL statements **before** running
  them. In pseudocode: `checked_query = sql_db_query_checker(query);
  sql_db_query(checked_query)`.
- Be creative and don't ask for permission! The database is ephemeral so it's OK to make some mistakes.
- The sqlite version is {sqlite3.sqlite_version} which supports multiple row inserts.
- Always prefer to insert multiple rows in a single call to the sql_db_query tool, if possible.
- You may request to execute multiple sql_db_query tool calls which will be run in parallel.

You can use run_sql_tool to run sql queries against the current sqlite3 database.
You can use create_database_tool to create a new ephemeral sqlite3 database if one is not found in current state.
You should always check if database for current session exist before running sql queries by calling create_database_tool.
If you make a mistake, try to recover."""

INTRO_TEXT = """\
Starting agent using ephemeral SQLite DB {dbpath}. This demo allows you to chat with an Agent
that has full access to an ephemeral SQLite database. The database is initially empty. It is
built with the the LangGraph prebuilt **ReAct Agent** and the **SQLDatabaseToolkit**. Here are some samples you can try:

**Weather**
- Create a new table to hold weather data.
- Populate the weather database with 20 example rows.
- Add a new column for weather observer notes

**Pets**
- Create a database table for pets including an `owner_id` column.
- Add 20 example rows please.
- Create an owner table.
- Link the two tables together, adding new columns, values, and rows as needed.
- Write a query to join these tables and give the result of owners and their pets.
- Show me the query, then the output as a table

---
"""

root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash",
    description=INTRO_TEXT,
    instruction=SYSTEM_PROMPT,
    tools=[run_sql_tool, create_database_tool],
)
