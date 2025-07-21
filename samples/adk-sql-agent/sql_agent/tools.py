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


import logging
from typing import Any, NotRequired, TypedDict
from opentelemetry import trace
from google.adk.tools import ToolContext
import sqlite3
import tempfile

SESSION_DB_KEY = "session_sqlite_db"

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class SqlRunResult(TypedDict):
    error: NotRequired[str]
    """If the result represents an error. It will be null or undefined if no error"""

    rows: NotRequired[list[tuple[str, ...]]]
    """The rows returned by the SQL query"""

@tracer.start_as_current_span("create_database")
def create_database_tool(tool_context: ToolContext) -> dict[str, Any]:
    """Creates a temporary file in the /tmp directory to hold an ephemeral
    sqlite3 database if a database is not found for the current session.
    """
    if not SESSION_DB_KEY in tool_context.state:
        _, path = tempfile.mkstemp(suffix=".db")
        # No scope prefix in the state data indicates that it will be persisted for
        # current session.
        # See https://google.github.io/adk-docs/sessions/state/.
        tool_context.state[SESSION_DB_KEY] = path
        return {"resp": "Created an ephemeral database"}
    return {"resp": f"Skipping database creation, {tool_context.state[SESSION_DB_KEY]} already exists"}

@tracer.start_as_current_span("run_sql")
def run_sql_tool(sql_query: str, tool_context: ToolContext) -> dict[str, Any]:
    """Runs a SQLite query. The SQL query can be DDL or DML. Returns the rows if it's a SELECT query."""
    current_session_db_path = tool_context.state.get(SESSION_DB_KEY)
    if current_session_db_path is None:
        return {"error": "Failed to find a database fo this session"}

    with sqlite3.connect(current_session_db_path) as db:
        try:
            cursor = db.cursor()
            cursor.execute(sql_query)
            rows_list: list[tuple[str, ...]] = []

            # Check if the query is one that would return rows (e.g., SELECT)
            if cursor.description is not None:
                fetched_rows: list[tuple[Any, ...]] = cursor.fetchall()
                rows_list = [tuple(str(col) for col in row) for row in fetched_rows]
                logger.info("Query returned %s rows", len(rows_list))
            else:
                # For DDL/DML (like INSERT, UPDATE, DELETE without RETURNING clause)
                # cursor.description is None.
                # rowcount shows number of affected rows for DML.
                logger.info("Query affected %s rows (DDL/DML)", cursor.rowcount)

            # DML statements (INSERT, UPDATE, DELETE) require a commit.
            # DDL statements are often autocommitted by SQLite, but an explicit commit here ensures DML changes are saved.
            db.commit()
            return {"rows": rows_list}

        except sqlite3.Error as err:
            logger.error(f"SQL Error: {err} for query: {sql_query}")
            try:
                db.rollback()  # Attempt to rollback on error
                logger.info("SQL transaction rolled back due to error.")
            except sqlite3.Error as rb_err:
                # This can happen if the connection is already closed or in an unusable state.
                logger.error(f"Failed to rollback transaction: {rb_err}")
            return {"error": str(err)}
