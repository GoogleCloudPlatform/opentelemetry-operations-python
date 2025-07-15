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
import sqlite3


tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class SqlRunResult(TypedDict):
    error: NotRequired[str]
    """If the result represents an error. It will be null or undefined if no error"""

    rows: NotRequired[list[tuple[str, ...]]]
    """The rows returned by the SQL query"""


def create_run_sql_tool(dbpath: str):
    @tracer.start_as_current_span("run_sql")
    def run_sql(sql_query: str) -> dict[str, Any]:
        """Runs a SQLite query. The SQL query can be DDL or DML. Returns the rows if it's a SELECT query."""

        with sqlite3.connect(dbpath) as db:
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

    return run_sql
